"""judge agent for adaptive rag"""

import os
from typing import Dict, Any, Optional
from openai import OpenAI

# judge metrics
FAITHFULNESS = "faithfulness"
RELEVANCE = "relevance"
COMPLETENESS = "completeness"

class JudgeAgent:
    def __init__(self, client: Optional[OpenAI] = None):
        self.client = client
        # default to cheap/fast model for judging
        self.model = "openai/gpt-4o-mini" 

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
            "2. Relevance: Does the answer directly address the user's query?\n"
            "3. Completeness: Does it answer the whole question or just a part?\n\n"
            "Output JSON format:\n"
            "{\n"
            '  "faithfulness_score": int (1-5),\n'
            '  "relevance_score": int (1-5),\n'
            '  "completeness_score": int (1-5),\n'
            '  "overall_score": float (0.0-1.0), // normalized average\n'
            '  "reasoning": "brief explanation",\n'
            '  "suggestion": "what is missing or needs fixing"\n'
            "}"
        )

        user_prompt = (
            f"User Query: {query}\n\n"
            f"Retrieved Context:\n{context[:10000]}... (truncated)\n\n" # truncate context to save judge tokens
            f"Generated Answer: {answer}\n\n"
            "Evaluate:"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            # adaptive logic: mostly concerned with low relevance or completeness
            # faithfulness should ideally be high; if low, it's a hallucination
            
            score = result.get("overall_score", 0.0)
            reason = result.get("reasoning", "")
            
            # threshold: if score < 0.7 (approx 3.5/5), trigger refinement
            needs_refinement = score < 0.7
            
            return {
                "score": score,
                "reason": reason,
                "needs_refinement": needs_refinement,
                "details": result
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
