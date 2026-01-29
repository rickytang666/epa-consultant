import os
import sys
import pytest
from dotenv import load_dotenv

# load env vars
load_dotenv()

# add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from ml.rag_pipeline import query_rag

# only run if explicitly requested or env var set, to save costs
# usage: uv run pytest tests/test_rag_quality.py
@pytest.mark.skipif(not os.getenv("OPENROUTER_API_KEY") and not os.getenv("GOOGLE_API_KEY"), reason="missing api key")
class TestRAGQuality:
    
    def get_answer(self, query):
        """helper to get full string answer"""
        chunks = list(query_rag(query))
        # filter for content type and join deltas
        text = "".join([c["delta"] for c in chunks if c["type"] == "content"])
        # normalize unicode hyphens from pdf
        return text.replace("‑", "-")

    def test_q1_pgp_definition(self):
        """Question 1: What is the PGP?"""
        query = "What is the PGP?"
        answer = self.get_answer(query)
        print(f"\nQ: {query}\nA: {answer}\n")
        
        # expectations: mentions pesticide general permit, discharge, epa
        assert "Pesticide General Permit" in answer or "PGP" in answer
        assert "EPA" in answer
        
    def test_q2_noi_requirement(self):
        """Question 2: Who needs to submit an NOI?"""
        query = "Who needs to submit an NOI?"
        answer = self.get_answer(query)
        print(f"\nQ: {query}\nA: {answer}\n")
        
        # expectations: decision-makers, threshold, criteria
        assert "Decision-maker" in answer or "Operator" in answer
        assert "NOI" in answer

    def test_q3_eligibility(self):
        """Question 3: What are the eligibility criteria?"""
        query = "What are the eligibility criteria?"
        answer = self.get_answer(query)
        print(f"\nQ: {query}\nA: {answer}\n")
        
        # expectations: coverage, waters of the US, endangered species
        assert "eligible" in answer or "criteria" in answer
        
    def test_q4_compliance_dates(self):
        """Question 4: What are the key dates for the permit?"""
        query = "What are the key dates for the permit (effective/expiration)?"
        answer = self.get_answer(query)
        print(f"\nQ: {query}\nA: {answer}\n")
        
        # expectations: 2026, 2031 (based on chunk_002-1 content)
        assert "2026" in answer
        assert "2031" in answer
        
    def test_q5_operator_definition(self):
        """Question 5: How does the EPA define an Operator?"""
        query = "How does the EPA define an Operator?"
        answer = self.get_answer(query)
        print(f"\nQ: {query}\nA: {answer}\n")
        
        # expectations: Applicator, Decision-maker, control
        assert "Applicator" in answer
        assert "Decision-maker" in answer
