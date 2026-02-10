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

        lowered = text.lower()
        
        # --- Convert sentiment, category and keywords into churn risk ---
        # Keyword churn intent signals
        keywords = ["cancel", "refund", "unsubscribe", "close account", "switch", "terminate"]
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
        except Exception:
            # if sentiment fails, keep sentiment_data None and continue
            logger.warning("Sentiment analysis failed during churn computation", exc_info=True)

        # Suggestion phrases: treat as mild positive intent (override noisy sentiment)
        SUGGESTION_KEYWORDS = [
            "please add", "add", "could you", "would you", "would love", "feature request", "please implement",
        ]
        suggestion_present = any(kw in lowered for kw in SUGGESTION_KEYWORDS)

        # If sentiment_data exists, possibly override for suggestions
        if sentiment_data is not None:
            s_label = sentiment_data.get("sentiment")
            s_conf = float(sentiment_data.get("confidence", 0.0))
            # If this looks like a suggestion and model scored it as negative or low-confidence,
            # override to a moderate positive sentiment to avoid mis-classifying feature requests.
            if suggestion_present and (s_label == "negative" or s_conf < 0.6):
                sentiment_data = {
                    "text": text,
                    "sentiment": "positive",
                    "confidence": 0.56,
                    "positive_score": 0.56,
                    "negative_score": 0.44,
                }

        # derive sentiment_signal used for churn (negative contribution only)
        if sentiment_data is not None and sentiment_data.get("sentiment") == "negative" and keyword_signal > 0.0:
            sentiment_signal = float(sentiment_data.get("confidence", 0.0))
        else:
            sentiment_signal = 0.0

        # Category signal mapping (business risk per category)
        category_map = {
            "billing": 1.0,
            "account": 0.9,
            "technical": 0.6,
            "support delay": 0.5,
            "feature request": 0.2,
            "general inquiry": 0.1,
            "other": 0.2,  # Low priority for unclassifiable/low-confidence text
            # map common labels from the classifier to sensible defaults
            "refund request": 1.0,
            "service complaint": 0.6,
            "feature": 0.2,
        }
        cat = result.get("category", "").lower()
        category_signal = category_map.get(cat, 0.1)

        # --- Post-process category overrides based on strong keywords ---
        # ONLY override non-"Other" categories. If classifier says "Other" (low confidence),
        # respect that and don't force it to a category.
        TECH_KEYWORDS = [
            "stuck", "freeze", "freezing", "crash", "crashes", "crashing",
            "not working", "keeps getting stuck", "keep getting stuck", "app", "phone",
            "mobile", "unresponsive", "hang", "hangs",
        ]
        if cat != "other" and any(k in lowered for k in TECH_KEYWORDS):
            # Only override to Technical if classifier didn't already say "Other"
            if cat != "technical":
                logger.info("Overriding category to Technical based on keywords")
            cat = "technical"
            result["category"] = "Technical"
            category_signal = category_map.get("technical", category_signal)

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

        # ------------------ Priority computation ------------------
        # Sentiment severity: negative sentiment confidence, for positive use a reduced multiplier
        sentiment_severity = 0.0
        sentiment_confidence = 0.0
        if sentiment_data is not None:
            sentiment_confidence = float(sentiment_data.get("confidence", 0.0))
            if sentiment_data.get("sentiment") == "negative":
                sentiment_severity = sentiment_confidence
            else:
                # positive sentiment should still influence priority moderately
                POSITIVE_SEVERITY_MULTIPLIER = 0.9
                sentiment_severity = sentiment_confidence * POSITIVE_SEVERITY_MULTIPLIER

        # Category priority mapping (business urgency)
        CATEGORY_PRIORITY = {
            "billing": 0.9,
            "account": 1.0,
            "refund request": 0.85,
            "technical": 0.7,
            "feature": 0.3,
            "general": 0.2,
        }
        category_priority = CATEGORY_PRIORITY.get(cat, 0.2)

        # Urgency keywords
        URGENT_KEYWORDS = [
            "urgent", "immediately", "asap",
            "not working", "down", "failed",
            "blocked", "cannot access",
        ]
        urgency_signal = 1.0 if any(k in lowered for k in URGENT_KEYWORDS) else 0.0

        # Confidence multiplier
        confidence_multiplier = 1.0
        if sentiment_confidence > 0.8:
            confidence_multiplier = 1.1

        # Priority score
        priority_score = (
            0.4 * sentiment_severity +
            0.35 * category_priority +
            0.25 * urgency_signal
        )
        priority_score *= confidence_multiplier
        priority_score = min(priority_score, 1.0)

        if priority_score >= 0.75:
            priority_label = "P1 – Critical"
        elif priority_score >= 0.5:
            priority_label = "P2 – High"
        elif priority_score >= 0.3:
            priority_label = "P3 – Medium"
        else:
            priority_label = "P4 – Low"

        if sentiment_data is not None and sentiment_data.get("sentiment") == "positive":
            priority_score = 0.0
            priority_label = "P4 – Low"
            logger.info(f"Overridden to P4 due to positive sentiment for text: '{text[:50]}...'")
        # include sentiment fields in predict response for UI
        sentiment_label_out = None
        sentiment_score_out = None
        if sentiment_data is not None:
            sentiment_label_out = sentiment_data.get("sentiment")
            # prefer positive_score if available
            sentiment_score_out = float(sentiment_data.get("positive_score") if sentiment_data.get("positive_score") is not None else sentiment_data.get("confidence", 0.0))

        return PredictResponse(
            category=result["category"],
            probabilities=result["probabilities"],
            label=result["category"],
            churn_probability=float(churn_risk),
            churn_label=churn_label,
            priority_score=float(priority_score),
            priority=priority_label,
            sentiment_label=sentiment_label_out,
            sentiment_score=sentiment_score_out,
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