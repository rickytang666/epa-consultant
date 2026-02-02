import asyncio
import os
from dotenv import load_dotenv

# Load env (searches current and parent dirs)
load_dotenv()

from ml.rag_pipeline import query_rag
async def run_debug():
    questions = [
        "When does this permit expire?",
        "What are the specific deadlines for filing an NOI for a new decision-maker?"
    ]

    print("=== DEBUGGING RAG PIPELINE ===\n")

    for q in questions:
        print(f"QUESTION: {q}")
        print("-" * 40)
        
        # Capture context and answer
        context_items = []
        answer_parts = []
        
        async for chunk in query_rag(q):
            if chunk["type"] == "sources":
                for source in chunk["data"]:
                    context_items.append(source)
            elif chunk["type"] == "content":
                answer_parts.append(chunk["delta"])
        
        full_answer = "".join(answer_parts)
        
        print(f"GENERATED ANSWER:\n{full_answer}\n")
        print("RETRIEVED CONTEXT (Top 3):")
        for i, ctx in enumerate(context_items[:3]):
            content = ctx.get('text', '')[:200].replace('\n', ' ')
            meta = ctx.get('metadata', {})
            print(f"[{i+1}] {meta.get('header_path_str', 'Unknown')} | {content}...")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_debug())
