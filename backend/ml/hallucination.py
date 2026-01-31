"""hallucination detection using cross-encoders"""

from sentence_transformers import CrossEncoder

class HallucinationDetector:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        # this model is trained to score (query, passage) relevance
        # we repurpose it to score (answer, context) support
        self.model = CrossEncoder(model_name)
        
    def compute_score(self, context: str, answer: str) -> float:
        """
        compute verification score (0 to 1).
        higher score = answer is more supported by context.
        """
        if not context or not answer:
             return 0.0

        # truncate if too long (model limit usually 512 tokens)
        # we just take the first chunks of both
        input_pair = (answer[:1000], context[:2000])
        
        # predict returns a logit score (unbounded) for ms-marco
        # we need to sigmoid it if we want 0-1, but the raw score is fine for thresholding
        # actually ms-marco-MiniLM-L-6-v2 output is raw logits.
        
        scores = self.model.predict([input_pair])
        score = float(scores[0])
        
        # normalize roughly to 0-1 for user display (sigmoid)
        import math
        try:
            sigmoid_score = 1 / (1 + math.exp(-score))
            return sigmoid_score
        except:
            return 0.0
