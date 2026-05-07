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
    audit_hash: Optional[str] = None
    risk_level: Optional[str] = None


class FullPredictionResponse(PredictionResponse):
    tabular_probabilities: List[float]
    audio_probabilities: List[float]
    audio_source: str


class StressVoicePredictionResponse(PredictionResponse):
    stress_baseline: float
    stress_neuroguard: float
    final_stress: float
    weight_baseline: float
    weight_neuroguard: float
    health_baseline: float
    health_neuroguard: float
    orchestrator_mode: str
    orchestrator_window_scope: str
    orchestrator_window_size: int
    baseline_source: str
    neuroguard_source: str
    baseline_available: bool
    blend: Dict[str, float]


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
    voice_enrolments: List[Dict[str, Any]] = Field(default_factory=list)
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)


class StudentProfileRequest(BaseModel):
    name: str


class ConsentRequest(BaseModel):
    student_id: str
    data_collection: bool = True
    ml_processing: bool = True
    zk_fl: bool = True
    raw_audio_storage: bool = False
    expires_at: Optional[str] = None


class VoiceEnrolmentResponse(BaseModel):
    id: Optional[str] = None
    student_id: str
    sample_count: int
    z_vector: List[float]
    audio_hashes: List[str]
    created_at: Optional[str] = None
