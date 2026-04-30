from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SurveyPredictionRequest(BaseModel):
    responses: Dict[str, float] = Field(
        ..., description="Survey answers keyed by StressLevelDataset column names."
    )
    student_id: Optional[str] = None
    survey_id: Optional[str] = None
    save: bool = True


class SurveyCreateRequest(BaseModel):
    student_id: str
    responses: Dict[str, float]


class PredictionResponse(BaseModel):
    prediction: int
    confidence_0: float
    confidence_1: float
    confidence_2: float
    model_type: str
    confidence: float
    saved_prediction_id: Optional[str] = None


class FullPredictionResponse(PredictionResponse):
    tabular_probabilities: List[float]
    audio_probabilities: List[float]
    audio_source: str


class HealthResponse(BaseModel):
    status: str
    model_dir: str
    models_loaded: bool
    available_models: Dict[str, bool] = Field(default_factory=dict)


class StudentHistory(BaseModel):
    student: Dict[str, Any] | None = None
    surveys: List[Dict[str, Any]]
    predictions: List[Dict[str, Any]]
    audio_files: List[Dict[str, Any]]


class StudentProfileRequest(BaseModel):
    name: str
