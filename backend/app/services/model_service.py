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
        self.lstm_model = None
        self.loaded = False

    def load(self) -> None:
        required = [
            "neuroguard_rf.pkl",
            "neuroguard_fusion.pkl",
            "neuroguard_scaler.pkl",
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
        audio_model_path = self.model_dir / "neuroguard_audio.keras"
        audio_scaler_path = self.model_dir / "neuroguard_audio_scaler.pkl"
        lstm_model_path = self.model_dir / "neuroguard_lstm.keras"
        self.audio_model = load_model(audio_model_path) if audio_model_path.exists() else None
        self.audio_scaler = joblib.load(audio_scaler_path) if audio_scaler_path.exists() else None
        self.lstm_model = load_model(lstm_model_path) if lstm_model_path.exists() else None
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
        if self.audio_model is None or self.audio_scaler is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Audio prediction is unavailable because this model folder does "
                    "not contain neuroguard_audio.keras."
                ),
            )
        expected_features = getattr(self.audio_scaler, "n_features_in_", features.shape[0])
        if features.shape[0] != expected_features:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Audio feature mismatch: extracted {features.shape[0]} features, "
                    f"but the scaler expects {expected_features}."
                ),
            )
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
        if self.audio_model is None or self.audio_scaler is None:
            return np.array([1.0, 0.0, 0.0])
        neutral_features = np.zeros(124, dtype=np.float32)
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

    def predict_temporal_from_responses(self, responses: Dict[str, float]) -> Dict[str, float | int]:
        self._ensure_loaded()
        if self.lstm_model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Temporal LSTM prediction is unavailable in this model folder.",
            )
        missing = missing_fields(responses, BASE_SURVEY_FIELDS)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing survey fields: {', '.join(missing)}",
            )
        engineered = add_composite_features(responses)
        row = pd.DataFrame([[engineered[field] for field in self.feature_order]], columns=self.feature_order)
        scaled = self.scaler.transform(row)
        input_shape = getattr(self.lstm_model, "input_shape", (None, 8, len(self.feature_order)))
        timesteps = int(input_shape[1] or 8)
        sequence = np.repeat(scaled[:, np.newaxis, :], timesteps, axis=1)
        raw = self.lstm_model.predict(sequence, verbose=0)[0]
        probabilities = np.asarray(raw, dtype=float)
        total = probabilities.sum()
        probabilities = probabilities / total if total else np.array([1.0, 0.0, 0.0])
        return self._response(probabilities)

    def available_models(self) -> dict[str, bool]:
        return {
            "tabular_rf": self.rf is not None,
            "fusion_gb": self.fusion is not None,
            "audio_mlp": self.audio_model is not None,
            "audio_scaler": self.audio_scaler is not None,
            "temporal_lstm": self.lstm_model is not None,
        }
