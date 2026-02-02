import pytest
import os
import json
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric
from deepeval.models import DeepEvalBaseLLM
from openai import AsyncOpenAI, OpenAI
from ml.rag_pipeline import query_rag_sync

# set deepeval timeout to 10 minutes (600s) to handle slow endpoints
os.environ["DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE"] = "600"

# custom openai LLM for deepeval with prompt caching
class OpenAILLM(DeepEvalBaseLLM):
    def __init__(self, model_name="gpt-4o-mini"):
        self.model_name = model_name
        # deep-eval needs async generation for speed
        self.aclient = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

    def load_model(self):
        return self.aclient

    def generate(self, prompt: str) -> str:
        # synchronous fallback (should rarely be used by deepeval if async is avail)
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

    async def a_generate(self, prompt: str) -> str:
        try:
            response = await self.aclient.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

    def get_model_name(self):
        return self.model_name

# init judge with prompt caching enabled
openai_judge = OpenAILLM(model_name="gpt-4o")


# load golden dataset
def load_dataset():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(current_dir, "golden_dataset.json"), "r") as f:
        return json.load(f)

dataset = load_dataset()

@pytest.mark.parametrize("item", dataset)
def test_rag_quality(item):
    input_text = item["input"]
    expected_output = item["expected_output"]
    
    # run pipeline
    pipeline_generator = query_rag_sync(input_text)
    
    actual_output = ""
    retrieved_context = []
    
    for chunk in pipeline_generator:
        if chunk["type"] == "content":
            actual_output += chunk["delta"]
        elif chunk["type"] == "sources":
            for source in chunk["data"]:
                text = source.get("text", "")
                meta = source.get("metadata", {})
                if "header_path_str" in meta:
                    text = f"[Source: {meta['header_path_str']}]\n{text}"
                retrieved_context.append(text)
    
    # strip debug/status prefixes and confidence scores
    if "**Structuring answer...**" in actual_output:
        actual_output = actual_output.split("**Structuring answer...**", 1)[1].strip()
    
    if "**Confidence Score**" in actual_output:
        actual_output = actual_output.split("**Confidence Score**")[0].strip()

    test_case = LLMTestCase(
        input=input_text,
        actual_output=actual_output,
        expected_output=expected_output,
        retrieval_context=retrieved_context
    )

    # metrics using OpenAI with prompt caching
    faithfulness = FaithfulnessMetric(
        threshold=0.6, 
        model=openai_judge,
        include_reason=True
    )
    
    relevancy = AnswerRelevancyMetric(
        threshold=0.6, 
        model=openai_judge,
        include_reason=True
    )

    # measure metrics manually to collect scores
    faithfulness.measure(test_case)
    relevancy.measure(test_case)

    # store scores
    f_score = faithfulness.score
    r_score = relevancy.score
    
    print(f"\n[TestCase: {item['input'][:30]}...]")
    print(f"  Faithfulness: {f_score:.2f}")
    print(f"  Relevancy:    {r_score:.2f}")
    
    # Store globally for average calculation
    if not hasattr(test_rag_quality, "results"):
        test_rag_quality.results = []
    
    # Store detailed result
    result_entry = {
        "input": input_text,
        "f": f_score,
        "r": r_score,
        "f_reason": faithfulness.reason if not faithfulness.is_successful() else None,
        "r_reason": relevancy.reason if not relevancy.is_successful() else None,
        "passed": faithfulness.is_successful() and relevancy.is_successful()
    }
    test_rag_quality.results.append(result_entry)

# simple hook to print averages at the end
@pytest.fixture(scope="session", autouse=True)
def print_averages():
    yield
    # this runs after tests
    results = getattr(test_rag_quality, "results", [])
    if results:
        avg_f = sum(r["f"] for r in results) / len(results)
        avg_r = sum(r["r"] for r in results) / len(results)
        
        print("\n" + "="*80)
        print("FINAL EVALUATION REPORT")
        print("="*80)
        print(f"{'Question':<50} | {'Faith':<6} | {'Relev':<6} | {'Status'}")
        print("-" * 80)
        
        failed_count = 0
        for res in results:
            status = "PASS" if res["passed"] else "FAIL"
            if not res["passed"]:
                failed_count += 1
            # Truncate question for display
            q_display = (res['input'][:47] + '...') if len(res['input']) > 47 else res['input']
            print(f"{q_display:<50} | {res['f']:.2f}   | {res['r']:.2f}   | {status}")
            
            # Print reasons if failed
            if not res["passed"]:
                if res["f_reason"]:
                    print(f"  > Faithfulness Failure: {res['f_reason']}")
                if res["r_reason"]:
                    print(f"  > Relevancy Failure:    {res['r_reason']}")
                print("-" * 80)

        print("="*80)
        print(f"SUMMARY: {len(results) - failed_count}/{len(results)} Tests Passed")
        print(f"Average Faithfulness: {avg_f:.2f}")
        print(f"Average Relevancy:    {avg_r:.2f}")
        print("="*80 + "\n")

