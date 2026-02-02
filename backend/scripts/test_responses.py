
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Add backend to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from ml.rag_pipeline import query_rag

def load_dataset():
    # Path to golden dataset
    be_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_path = os.path.join(be_dir, "tests", "acceptance", "golden_dataset.json")
    
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}")
        sys.exit(1)
        
    with open(dataset_path, "r") as f:
        return json.load(f)

async def generate_responses():
    dataset = load_dataset()
    print(f"Loaded {len(dataset)} questions from golden_dataset.json\n")
    print("="*80)

    for i, item in enumerate(dataset):
        question = item["input"]
        print(f"Q{i+1}: {question}")
        print("-" * 40)
        
        answer_text = ""
        async for chunk in query_rag(question):
            if chunk["type"] == "content":
                answer_text += chunk["delta"]
        
        print(answer_text)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(generate_responses())
    except KeyboardInterrupt:
        print("\nAborted.")
    except Exception as e:
        print(f"\nError: {e}")
