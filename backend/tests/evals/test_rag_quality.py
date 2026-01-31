import pytest
import os
import json
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric
from deepeval.models import DeepEvalBaseLLM
from openai import AsyncOpenAI, OpenAI
from ml.rag_pipeline import query_rag

# custom openrouter LLM for deepeval
class OpenRouterLLM(DeepEvalBaseLLM):
    def __init__(self, model_name="openai/gpt-oss-120b"):
        self.model_name = model_name
        # deep-eval needs async generation for speed
        self.aclient = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    def load_model(self):
        return self.aclient

    def generate(self, prompt: str) -> str:
        # synchronous fallback (should rarely be used by deepeval if async is avail)
        # we create a temp sync client just for this blocking call
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
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

# init judge
openrouter_judge = OpenRouterLLM(model_name="openai/gpt-oss-120b")


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
    pipeline_generator = query_rag(input_text)
    
    actual_output = ""
    retrieved_context = []
    
    for chunk in pipeline_generator:
        if chunk["type"] == "content":
            actual_output += chunk["delta"]
        elif chunk["type"] == "sources":
            for source in chunk["data"]:
                retrieved_context.append(source.get("text", ""))
    
    if "**Confidence Score**" in actual_output:
        actual_output = actual_output.split("**Confidence Score**")[0].strip()

    test_case = LLMTestCase(
        input=input_text,
        actual_output=actual_output,
        expected_output=expected_output,
        retrieval_context=retrieved_context
    )

    # metrics using OpenRouter
    faithfulness = FaithfulnessMetric(
        threshold=0.7, 
        model=openrouter_judge,
        include_reason=True
    )
    
    relevancy = AnswerRelevancyMetric(
        threshold=0.7, 
        model=openrouter_judge,
        include_reason=True
    )

    assert_test(test_case, [faithfulness, relevancy])

