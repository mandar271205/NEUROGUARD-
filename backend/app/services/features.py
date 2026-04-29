import json
from pathlib import Path
from typing import Dict, Iterable, List


BASE_SURVEY_FIELDS = [
    "anxiety_level",
    "self_esteem",
    "mental_health_history",
    "depression",
    "headache",
    "blood_pressure",
    "sleep_quality",
    "breathing_problem",
    "noise_level",
    "living_conditions",
    "safety",
    "basic_needs",
    "academic_performance",
    "study_load",
    "teacher_student_relationship",
    "future_career_concerns",
    "social_support",
    "peer_pressure",
    "extracurricular_activities",
    "bullying",
]


DEFAULT_FEATURES = BASE_SURVEY_FIELDS + [
    "risk_score",
    "social_isolation",
    "env_stress",
]


def load_feature_order(model_dir: Path) -> List[str]:
    feature_file = model_dir / "neuroguard_features.json"
    if feature_file.exists():
        return json.loads(feature_file.read_text(encoding="utf-8"))
    return DEFAULT_FEATURES


def missing_fields(responses: Dict[str, float], fields: Iterable[str]) -> List[str]:
    return [field for field in fields if field not in responses]


def add_composite_features(responses: Dict[str, float]) -> Dict[str, float]:
    data = {key: float(value) for key, value in responses.items()}
    data.setdefault(
        "risk_score",
        (
            data["anxiety_level"] * 0.30
            + data["depression"] * 0.30
            + (10 - data["self_esteem"]) * 0.15
            + (10 - data["sleep_quality"]) * 0.15
            + data["study_load"] * 0.10
        ),
    )
    data.setdefault(
        "social_isolation",
        (10 - data["social_support"]) * 0.60 + data["peer_pressure"] * 0.40,
    )
    data.setdefault(
        "env_stress",
        (
            data["noise_level"] * 0.25
            + (10 - data["living_conditions"]) * 0.25
            + (10 - data["safety"]) * 0.25
            + (10 - data["basic_needs"]) * 0.25
        ),
    )
    return data
