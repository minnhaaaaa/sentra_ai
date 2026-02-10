from typing import List, Dict, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.exceptions import NotFittedError
import joblib
import logging

logger = logging.getLogger(__name__)

class TicketClassifier:
    def __init__(self, labels: Optional[List[str]] = None):
        self.labels = labels or [
            "Billing",
            "Technical",
            "Account",
            "Feature",
            "Refund Request",
            "Service Complaint",
            "Other",  # Added for edge cases and low-confidence predictions
        ]
        self.pipeline: Optional[Pipeline] = None
        self.confidence_threshold = 0.25  # With balanced training, legitimate predictions reach ~35-40%, ambiguous ones stay lower

    def build_pipeline(self) -> Pipeline:
        return Pipeline(
            [
                ("tfidf", TfidfVectorizer(min_df=1, ngram_range=(1, 2))),
                ("clf", LogisticRegression(max_iter=200)),
            ]
        )

    def train(self, texts: List[str], labels: List[str]):
        if not texts:
            raise ValueError("No training texts provided")
        # Ensure all labels are in self.labels (add "Other" if missing)
        unique_labels = set(labels)
        if "Other" not in unique_labels:
            # Optionally warn or add dummy data, but for now, proceed
            pass
        self.pipeline = self.build_pipeline()
        self.pipeline.fit(texts, labels)

    def predict(self, text: str) -> Dict[str, object]:
        if self.pipeline is None:
            raise NotFittedError("Model is not trained yet")
        
        # Handle edge cases: empty or very short text
        if not text or len(text.strip()) < 3:
            return {
                "category": "Other",
                "probabilities": {label: 0.0 for label in self.labels},  # All zero for edge case
            }
        
        pred = self.pipeline.predict([text])[0]
        probs = self.pipeline.predict_proba([text])[0]
        label_probs = {label: float(prob) for label, prob in zip(self.pipeline.classes_, probs)}
        
        # Ensure all known labels exist in the probs mapping (zero if absent)
        for lbl in self.labels:
            label_probs.setdefault(lbl, 0.0)
        
        # Confidence check: If max probability < threshold, classify as "Other"
        max_prob = max(label_probs.values())
        logger.debug(f"Text: '{text[:50]}...' | Prediction: {pred} | Max prob: {max_prob:.4f} | Threshold: {self.confidence_threshold} | All probs: {label_probs}")
        
        if max_prob < self.confidence_threshold:
            logger.info(f"Classifying as 'Other' due to low confidence (max_prob={max_prob:.4f} < threshold={self.confidence_threshold})")
            return {
                "category": "Other",
                "probabilities": label_probs,  # Keep original probs for transparency
            }
        
        return {"category": pred, "probabilities": label_probs}

    def save(self, path: str):
        if self.pipeline is None:
            raise NotFittedError("Model is not trained yet")
        joblib.dump({"pipeline": self.pipeline, "labels": self.labels, "confidence_threshold": self.confidence_threshold}, path)

    def load(self, path: str):
        data = joblib.load(path)
        self.pipeline = data["pipeline"]
        self.labels = data.get("labels", self.labels)
        self.confidence_threshold = data.get("confidence_threshold", 0.5)  # Default if not saved