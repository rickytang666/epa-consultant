
import sys
import os
# add backend to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml.hallucination import HallucinationDetector
import time

def test_hallucination_detection():
    print("Initializing detector (may download model)...")
    start = time.time()
    detector = HallucinationDetector()
    print(f"Initialization took {time.time() - start:.2f}s")
    
    # case 1: clear entailment
    context = "The EPA was established on December 2, 1970."
    answer = "The Environmental Protection Agency was founded in 1970."
    score = detector.compute_score(context, answer)
    print(f"Case 1 (Entailment): Score = {score:.4f} (Expected: High)")
    
    # case 2: clear hallucination
    context = "The EPA was established on December 2, 1970."
    answer = "The EPA was founded in 1899 by Theodore Roosevelt."
    score = detector.compute_score(context, answer)
    print(f"Case 2 (Hallucination): Score = {score:.4f} (Expected: Low)")
    
    # case 3: partial/neutral
    context = "The EPA allows discharges under the PGP."
    answer = "The permit covers mosquito control."
    score = detector.compute_score(context, answer)
    print(f"Case 3 (Neutral/Relevant): Score = {score:.4f}")

if __name__ == "__main__":
    test_hallucination_detection()
