from typing import Dict, Optional
import logging
from transformers import pipeline

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Sentiment analyzer using DistilBERT model.
    Classifies text into positive or negative sentiment.
    """

    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"):
        """
        Initialize the sentiment analyzer with the specified model.
        Model loads on first use (lazy loading - does not block startup).
        
        Args:
            model_name: Hugging Face model identifier
        """
        self.model_name = model_name
        self.pipeline = None
        self.model_loaded = False

    def _load_model(self):
        """Load the sentiment classification pipeline (lazy loading on first use)."""
        if self.model_loaded:
            return
            
        try:
            logger.info(f"Loading sentiment model: {self.model_name}")
            # import transformers.pipeline lazily so the module import doesn't fail at app startup
            from transformers import pipeline

            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model_name,
                device=-1,  # Use CPU; change to 0 for GPU
                truncation=True,
                top_k=None  # Return scores for all labels (positive and negative)
            )
            self.model_loaded = True
            logger.info("✓ Sentiment model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sentiment model: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to load sentiment model: {str(e)}")

    def analyze(self, text: str) -> Dict[str, object]:
        """
        Analyze sentiment of input text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary with sentiment classification and confidence score
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")
        
        # Load model on first use (lazy loading)
        if not self.model_loaded:
            self._load_model()
        
        if self.pipeline is None:
            raise RuntimeError("Model not loaded")
        
        try:
            # Let the pipeline handle truncation (up to 512 tokens)
            result = self.pipeline(text)
            
            # result is a list of dicts: [{"label": "NEGATIVE", "score": prob_neg}, {"label": "POSITIVE", "score": prob_pos}]
            scores = {item["label"].lower(): item["score"] for item in result[0]}
            positive_score = scores.get("positive", 0.0)
            negative_score = scores.get("negative", 0.0)
            
            # Determine sentiment based on higher score
            if positive_score > negative_score:
                sentiment = "positive"
                confidence = positive_score
            else:
                sentiment = "negative"
                confidence = negative_score
            
            logger.debug(f"Sentiment analysis: {sentiment} ({confidence:.4f})")
            
            return {
                "text": text,
                "sentiment": sentiment,
                "confidence": float(confidence),
                "positive_score": float(positive_score),
                "negative_score": float(negative_score),
            }
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Sentiment analysis failed: {str(e)}")

    def batch_analyze(self, texts: list) -> list:
        """
        Analyze sentiment for multiple texts.
        
        Args:
            texts: List of input texts to analyze
            
        Returns:
            List of sentiment analysis results
        """
        if not texts:
            raise ValueError("Input texts list cannot be empty")
        
        # Load model on first use (lazy loading)
        if not self.model_loaded:
            self._load_model()
        
        if self.pipeline is None:
            raise RuntimeError("Model not loaded")
        
        try:
            # Let the pipeline handle truncation
            results = self.pipeline(texts)
            
            analysis_results = []
            for text, result in zip(texts, results):
                scores = {item["label"].lower(): item["score"] for item in result}
                positive_score = scores.get("positive", 0.0)
                negative_score = scores.get("negative", 0.0)
                
                if positive_score > negative_score:
                    sentiment = "positive"
                    confidence = positive_score
                else:
                    sentiment = "negative"
                    confidence = negative_score
                
                analysis_results.append({
                    "text": text,
                    "sentiment": sentiment,
                    "confidence": float(confidence),
                    "positive_score": float(positive_score),
                    "negative_score": float(negative_score),
                })
            
            logger.debug(f"Batch analysis completed: {len(analysis_results)} texts")
            return analysis_results
        except Exception as e:
            logger.error(f"Batch sentiment analysis failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Batch sentiment analysis failed: {str(e)}")