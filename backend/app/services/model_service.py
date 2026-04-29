from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from fastapi import HTTPException, UploadFile, status

from app.services.audio_features import extract_audio_features
from app.services.features import BASE_SURVEY_FIELDS, add_composite_features, load_feature_order, missing_fields


class NeuroGuardModels:
    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self.feature_order = load_feature_order(model_dir)
        self.rf = None
        self.fusion = None
        self.scaler = None
        self.audio_model = None
        self.audio_scaler = None
        self.loaded = False

    def load(self) -> None:
        required = [
            "neuroguard_rf.pkl",
            "neuroguard_fusion.pkl",
            "neuroguard_scaler.pkl",
            "neuroguard_audio.keras",
            "neuroguard_audio_scaler.pkl",
        ]
        missing = [name for name in required if not (self.model_dir / name).exists()]
        if missing:
            raise FileNotFoundError(
                f"Missing model files in {self.model_dir}: {', '.join(missing)}"
            )

        from tensorflow.keras.models import load_model

        self.rf = joblib.load(self.model_dir / "neuroguard_rf.pkl")
        self.fusion = joblib.load(self.model_dir / "neuroguard_fusion.pkl")
        self.scaler = joblib.load(self.model_dir / "neuroguard_scaler.pkl")
        self.audio_model = load_model(self.model_dir / "neuroguard_audio.keras")
        self.audio_scaler = joblib.load(self.model_dir / "neuroguard_audio_scaler.pkl")
        self.loaded = True

    def _ensure_loaded(self) -> None:
        if not self.loaded:
            self.load()

    @staticmethod
    def _align_probabilities(model, raw_probs: np.ndarray) -> np.ndarray:
        probs = np.zeros(3, dtype=float)
        classes = getattr(model, "classes_", np.array([0, 1, 2]))
        for index, label in enumerate(classes):
            if int(label) in (0, 1, 2):
                probs[int(label)] = float(raw_probs[index])
        total = probs.sum()
        return probs / total if total else np.array([1.0, 0.0, 0.0])

    @staticmethod
    def _response(probabilities: np.ndarray) -> Dict[str, float | int]:
        prediction = int(np.argmax(probabilities))
        confidence = float(probabilities[prediction])
        return {
            "prediction": prediction,
            "confidence_0": float(probabilities[0]),
            "confidence_1": float(probabilities[1]),
            "confidence_2": float(probabilities[2]),
            "confidence": confidence,
        }

    def tabular_probabilities(self, responses: Dict[str, float]) -> np.ndarray:
        self._ensure_loaded()
        missing = missing_fields(responses, BASE_SURVEY_FIELDS)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing survey fields: {', '.join(missing)}",
            )

        engineered = add_composite_features(responses)
        row = pd.DataFrame([[engineered[field] for field in self.feature_order]], columns=self.feature_order)
        scaled = self.scaler.transform(row)
        raw_probs = self.rf.predict_proba(scaled)[0]
        return self._align_probabilities(self.rf, raw_probs)

    def predict_tabular(self, responses: Dict[str, float]) -> Dict[str, float | int]:
        probabilities = self.tabular_probabilities(responses)
        return self._response(probabilities)

    def audio_probabilities_from_features(self, features: np.ndarray) -> np.ndarray:
        self._ensure_loaded()
        scaled = self.audio_scaler.transform(features.reshape(1, -1))
        raw = self.audio_model.predict(scaled, verbose=0)[0]
        raw = np.asarray(raw, dtype=float)
        total = raw.sum()
        return raw / total if total else np.array([1.0, 0.0, 0.0])

    async def audio_probabilities_from_upload(self, upload: UploadFile) -> Tuple[np.ndarray, np.ndarray]:
        suffix = Path(upload.filename or "audio.wav").suffix or ".wav"
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await upload.read())
            tmp_path = Path(tmp.name)
        try:
            features = extract_audio_features(tmp_path)
            probabilities = self.audio_probabilities_from_features(features)
            return probabilities, features
        finally:
            tmp_path.unlink(missing_ok=True)

    def synthetic_audio_probabilities(self) -> np.ndarray:
        neutral_features = np.zeros(85, dtype=np.float32)
        return self.audio_probabilities_from_features(neutral_features)

    def predict_audio_from_probabilities(self, probabilities: np.ndarray) -> Dict[str, float | int]:
        return self._response(probabilities)

    def predict_full(self, tabular_probs: np.ndarray, audio_probs: np.ndarray) -> Dict[str, float | int]:
        self._ensure_loaded()
        fusion_input = np.concatenate([tabular_probs, audio_probs]).reshape(1, -1)
        if hasattr(self.fusion, "predict_proba"):
            raw_probs = self.fusion.predict_proba(fusion_input)[0]
            probabilities = self._align_probabilities(self.fusion, raw_probs)
        else:
            label = int(self.fusion.predict(fusion_input)[0])
            probabilities = np.zeros(3, dtype=float)
            probabilities[label] = 1.0
        return self._response(probabilities)
