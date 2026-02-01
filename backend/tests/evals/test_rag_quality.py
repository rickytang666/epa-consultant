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
openai_judge = OpenAILLM(model_name="gpt-4o-mini")


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
                retrieved_context.append(source.get("text", ""))
    
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
        threshold=0.7, 
        model=openai_judge,
        include_reason=True
    )
    
    relevancy = AnswerRelevancyMetric(
        threshold=0.7, 
        model=openai_judge,
        include_reason=True
    )

    assert_test(test_case, [faithfulness, relevancy])

