"""judge agent for adaptive rag"""

import os
from typing import Dict, Any, Optional
from openai import OpenAI
from pydantic import BaseModel, Field

# judge metrics
FAITHFULNESS = "faithfulness"
RELEVANCE = "relevance"
COMPLETENESS = "completeness"

class EvaluationResult(BaseModel):
    reasoning: str = Field(description="First, analyze the answer based on the context and query. Provide a brief explanation of your scoring.")
    suggestion: str = Field(description="Suggestions for improvement if the answer is not perfect.")
    faithfulness_score: int = Field(description="Score 1-5. 1=Hallucination/Contradiction, 5=Fully supported by context.")
    relevance_score: int = Field(description="Score 1-5. 1=Irrelevant, 5=Direct, concise, and complete answer.")
    completeness_score: int = Field(description="Score 1-5. 1=Misses core question, 5=Fully answers all parts.")

class JudgeAgent:
    def __init__(self, client: Optional[OpenAI] = None):
        self.client = client
        self.model = "openai/gpt-oss-120b" 

    def evaluate_answer(self, query: str, context: str, answer: str) -> Dict[str, Any]:
        """
        evaluate the generated answer against query and context.
        returns:
            {
                "score": float (0-1),
                "reason": str,
                "needs_refinement": bool
            }
        """
        if not self.client:
            return {"score": 1.0, "reason": "no judge client", "needs_refinement": False}

        system_prompt = (
            "You are an expert RAG system evaluator. "
            "Your job is to evaluate the quality of an AI-generated Answer based on the User Query and Retrieved Context.\n"
            "Evaluate on these criteria:\n"
            "1. Faithfulness: Is the answer derived ONLY from the context? (No hallucinations)\n"
            "   - 1: Completely hallucinates or contradicts context.\n"
            "   - 3: Mostly grounded but has minor external info or inaccuracies.\n"
            "   - 5: 100% supported by context statements.\n"
            "2. Relevance: Does the answer directly address the user's query?\n"
            "   - 1: Completely irrelevant.\n"
            "   - 3: Relevant but contains unnecessary info or is too verbose.\n"
            "   - 5: Direct, concise, and complete answer to the query.\n"
            "3. Completeness: Does it answer the whole question or just a part?\n"
            "   - 1: Misses the core question.\n"
            "   - 3: Partial answer.\n"
            "   - 5: Fully answers all parts of the question."
        )

        user_prompt = (
            f"User Query: {query}\n\n"
            f"Retrieved Context:\n{context[:10000]}... (truncated)\n\n" # truncate context to save judge tokens
            f"Generated Answer: {answer}\n\n"
            "Evaluate:"
        )

        try:
            # using beta.parse for structured outputs
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=EvaluationResult,
                temperature=0.0
            )
            
            result = completion.choices[0].message.parsed
            
            # calculate overall score manually (average of 3 scores, normalized to 0-1)
            # (f + r + c) / 3 / 5 
            avg_score = (result.faithfulness_score + result.relevance_score + result.completeness_score) / 3.0
            overall_score = avg_score / 5.0
            
            # threshold: if score < 0.7 (approx 3.5/5), trigger refinement
            needs_refinement = overall_score < 0.7
            
            return {
                "score": overall_score,
                "reason": result.reasoning,
                "needs_refinement": needs_refinement,
                "details": {
                    "faithfulness_score": result.faithfulness_score,
                    "relevance_score": result.relevance_score,
                    "completeness_score": result.completeness_score,
                    "reasoning": result.reasoning,
                    "suggestion": result.suggestion
                }
            }

        except Exception as e:
            print(f"Judge error: {e}")
            return {"score": 1.0, "reason": "judge failed", "needs_refinement": False}

    def suggest_refined_query(self, query: str, feedback: str) -> str:
        """
        generate a search query to address missing info
        """
        if not self.client:
            return query
            
        system_prompt = (
            "You are a search query optimizer. "
            "The previous retrieval failed to provide enough context. "
            "Based on the user query and the missing information feedback, generate a new, focused search query."
        )
        
        user_prompt = f"Original Query: {query}\nFeedback: {feedback}\n\nNew Search Query:"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except:
            return query
