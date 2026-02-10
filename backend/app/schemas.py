from pydantic import BaseModel
from typing import List, Dict, Optional


class PredictRequest(BaseModel):
    text: str


class PredictResponse(BaseModel):
    category: str
    label: Optional[str] = None
    probabilities: Dict[str, float]
    churn_probability: Optional[float] = None
    churn_label: Optional[str] = None


class TrainExample(BaseModel):
    text: str
    label: str


class TrainRequest(BaseModel):
    examples: List[TrainExample]


class TrainResponse(BaseModel):
    success: bool
    trained_on: int


class SentimentRequest(BaseModel):
    text: str


class SentimentResponse(BaseModel):
    text: str
    sentiment: str
    confidence: float
    positive_score: float
    negative_score: float


class BatchSentimentRequest(BaseModel):
    texts: List[str]


class BatchSentimentResponse(BaseModel):
    results: List[SentimentResponse]
