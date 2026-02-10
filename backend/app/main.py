from fastapi import FastAPI, HTTPException
import logging
from fastapi.middleware.cors import CORSMiddleware
from .models.ticket_classifier import TicketClassifier
from .models.sentiment_analyzer import SentimentAnalyzer
from .schemas import (
    PredictRequest, 
    PredictResponse, 
    TrainRequest, 
    TrainResponse,
    SentimentRequest,
    SentimentResponse,
    BatchSentimentRequest,
    BatchSentimentResponse
)
from .data.sample_data import SAMPLE_TRAINING
from typing import List
import os


MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "model.joblib")

app = FastAPI(title="Ticket Classifier API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

classifier = TicketClassifier()
sentiment_analyzer = None

# basic logging for debugging predict flows
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def initial_train():
    texts, labels = zip(*SAMPLE_TRAINING)
    classifier.train(list(texts), list(labels))
    try:
        classifier.save(MODEL_PATH)
    except Exception:
        # ignore save errors for environments without write permissions
        pass


@app.on_event("startup")
def startup_event():
    global sentiment_analyzer
    
    # Initialize sentiment analyzer (uses lazy loading - model loads on first use)
    try:
        logger.info("Initializing sentiment analyzer (lazy loading)...")
        sentiment_analyzer = SentimentAnalyzer()
        logger.info("✓ Sentiment analyzer ready (model will load on first use)")
    except Exception as e:
        logger.error(f"✗ Failed to initialize sentiment analyzer: {str(e)}", exc_info=True)
        sentiment_analyzer = None
    
    # Initialize ticket classifier
    try:
        logger.info("Initializing ticket classifier...")
        if os.path.exists(MODEL_PATH):
            logger.info(f"Loading saved model from {MODEL_PATH}")
            classifier.load(MODEL_PATH)
            logger.info("✓ Ticket classifier loaded successfully")
        else:
            logger.info("No saved model found, training on sample data...")
            initial_train()
            logger.info("✓ Ticket classifier trained successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize classifier: {str(e)}", exc_info=True)
        try:
            logger.info("Fallback: training on sample data...")
            initial_train()
            logger.info("✓ Fallback training completed")
        except Exception as e2:
            logger.error(f"✗ Fallback training failed: {str(e2)}", exc_info=True)


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text provided")
    try:
        if classifier.pipeline is None:
            raise HTTPException(status_code=503, detail="Classifier not trained yet")
        result = classifier.predict(text)
        logger.info(f"Predicted: '{text[:50]}...' -> {result['category']}")

        # --- Convert sentiment, category and keywords into churn risk ---
        # Keyword churn intent signals
        keywords = ["cancel", "refund", "unsubscribe", "close account", "switch", "terminate"]
        lowered = text.lower()
        matches = 0
        for kw in keywords:
            if kw in lowered:
                matches += 1
        keyword_signal = float(matches) / float(len(keywords)) if matches > 0 else 0.0

        # Sentiment signal: use sentiment analyzer if available (lazy loads model)
        # Only count negative sentiment towards churn if there is churn intent keyword evidence
        sentiment_signal = 0.0
        sentiment_data = None
        try:
            if sentiment_analyzer is not None:
                sentiment_data = sentiment_analyzer.analyze(text)
                # sentiment_data['sentiment'] is 'positive' or 'negative'
                if sentiment_data.get("sentiment") == "negative" and keyword_signal > 0.0:
                    sentiment_signal = float(sentiment_data.get("confidence", 0.0))
                else:
                    sentiment_signal = 0.0
        except Exception:
            # if sentiment fails, keep signal at 0 and continue
            logger.warning("Sentiment analysis failed during churn computation", exc_info=True)

        # Category signal mapping (business risk per category)
        category_map = {
            "billing": 1.0,
            "account": 0.9,
            "technical": 0.6,
            "support delay": 0.5,
            "feature request": 0.2,
            "general inquiry": 0.1,
            # map common labels from the classifier to sensible defaults
            "refund request": 1.0,
            "service complaint": 0.6,
            "feature": 0.2,
        }
        cat = result.get("category", "").lower()
        category_signal = category_map.get(cat, 0.1)

        # Combine into churn risk
        churn_risk = (0.5 * sentiment_signal) + (0.3 * category_signal) + (0.2 * keyword_signal)
        # clamp 0..1
        churn_risk = max(0.0, min(1.0, churn_risk))

        # Label churn risk for UI
        if churn_risk >= 0.66:
            churn_label = "High"
        elif churn_risk >= 0.33:
            churn_label = "Medium"
        else:
            churn_label = "Low"

        return PredictResponse(
            category=result["category"],
            probabilities=result["probabilities"],
            label=result["category"],
            churn_probability=float(churn_risk),
            churn_label=churn_label,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/train", response_model=TrainResponse)
def train(request: TrainRequest):
    examples = request.examples
    if not examples:
        raise HTTPException(status_code=400, detail="No training examples provided")
    texts = [ex.text for ex in examples]
    labels = [ex.label for ex in examples]
    classifier.train(texts, labels)
    try:
        classifier.save(MODEL_PATH)
    except Exception:
        pass
    return TrainResponse(success=True, trained_on=len(texts))


@app.get("/labels")
def get_labels():
    return {"labels": classifier.labels}


@app.post("/sentiment", response_model=SentimentResponse)
def analyze_sentiment(request: SentimentRequest):
    """Analyze sentiment of input text (positive or negative)"""
    if sentiment_analyzer is None:
        logger.error("Sentiment analyzer not initialized")
        raise HTTPException(status_code=503, detail="Sentiment analyzer not available. Please check server logs.")
    
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text provided")
    
    try:
        result = sentiment_analyzer.analyze(text)
        logger.info(f"Sentiment: '{text[:50]}...' -> {result['sentiment']} ({result['confidence']:.2%})")
        return SentimentResponse(
            text=result["text"],
            sentiment=result["sentiment"],
            confidence=result["confidence"],
            positive_score=result["positive_score"],
            negative_score=result["negative_score"]
        )
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")


@app.post("/sentiment/batch", response_model=BatchSentimentResponse)
def analyze_sentiment_batch(request: BatchSentimentRequest):
    """Analyze sentiment for multiple texts"""
    if sentiment_analyzer is None:
        logger.error("Sentiment analyzer not initialized")
        raise HTTPException(status_code=503, detail="Sentiment analyzer not available. Please check server logs.")
    
    if not request.texts:
        raise HTTPException(status_code=400, detail="Empty texts list provided")
    
    try:
        results = sentiment_analyzer.batch_analyze(request.texts)
        logger.info(f"Batch sentiment analysis: {len(results)} texts processed")
        
        sentiment_responses = [
            SentimentResponse(
                text=result["text"],
                sentiment=result["sentiment"],
                confidence=result["confidence"],
                positive_score=result["positive_score"],
                negative_score=result["negative_score"]
            )
            for result in results
        ]
        return BatchSentimentResponse(results=sentiment_responses)
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Batch sentiment analysis error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
