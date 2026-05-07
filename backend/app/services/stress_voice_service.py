from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import joblib
import librosa
import numpy as np

from app.services.audio_features import extract_audio_features
from app.services.adaptive_orchestrator import AdaptiveWeightingEngine, OrchestrationResult
from app.services.model_service import NeuroGuardModels


@dataclass
class BaselineResult:
    score: float
    source: str
    available: bool
    details: dict[str, Any]


@dataclass
class StudentResult:
    score: float
    source: str
    probabilities: np.ndarray


@dataclass
class StressVoiceResult:
    baseline: BaselineResult
    student: StudentResult
    final_stress: float
    probabilities: np.ndarray
    prediction: int
    confidence: float
    orchestration: OrchestrationResult


def probabilities_from_stress_score(score: float) -> np.ndarray:
    score = float(np.clip(score, 0.0, 1.0))
    high_risk = max(0.0, (score - 0.68) / 0.32)
    high_stress = max(0.0, 1.0 - abs(score - 0.56) / 0.44)
    normal = max(0.0, 1.0 - score)
    probs = np.array([normal, high_stress, high_risk], dtype=float)
    total = probs.sum()
    return probs / total if total else np.array([1.0, 0.0, 0.0])


class ExternalStressBackbone:
    DATASETS = ("ravdess", "cremad", "emodb", "shemo")
    GENDERS = ("female", "male")

    def __init__(self, repo_dir: Path) -> None:
        self.repo_dir = repo_dir
        self.independent_dir = repo_dir / "backbone_independent"
        self.raspi_dir = repo_dir / "speech_analysis_raspi"
        self._loaded_models: dict[tuple[str, str], Any] = {}

    def status(self) -> dict[str, Any]:
        h5_files = list(self.independent_dir.glob("base_store/saved_models/**/*.h5"))
        tflite_files = list(self.independent_dir.glob("base_store/saved_models/**/*.tflite"))
        config_files = [
            path
            for path in self.independent_dir.glob("base_store/saved_modelconfigs/**/*")
            if path.is_file()
        ]
        expected = self._expected_artifacts()
        available_slots = self._available_slots()
        missing_h5 = [str(paths[0]) for paths in expected["h5"] if not any(path.exists() for path in paths)]
        missing_tflite = [str(paths[0]) for paths in expected["tflite"] if not any(path.exists() for path in paths)]
        missing_configs = [str(paths[0]) for paths in expected["config"] if not any(path.exists() for path in paths)]
        return {
            "repo_dir": str(self.repo_dir),
            "module": "backbone_independent",
            "module_dir": str(self.independent_dir),
            "repo_exists": self.repo_dir.exists(),
            "license": "MIT" if (self.repo_dir / "LICENSE").exists() else "unknown",
            "h5_model_count": len(h5_files),
            "tflite_model_count": len(tflite_files),
            "model_config_count": len(config_files),
            "expected_slots": len(self.DATASETS) * len(self.GENDERS),
            "available_slots": [f"{dataset}/{gender}" for dataset, gender in available_slots],
            "missing_h5": missing_h5,
            "missing_tflite": missing_tflite,
            "missing_configs": missing_configs,
            "ready": bool(available_slots),
            "complete": not missing_h5 and not missing_configs,
            "tflite_ready": bool(available_slots) and not missing_tflite,
        }

    def _expected_artifacts(self) -> dict[str, list[list[Path]]]:
        return {
            "h5": [
                self._h5_candidates(dataset, gender)
                for dataset in self.DATASETS
                for gender in self.GENDERS
            ],
            "tflite": [
                self._tflite_candidates(dataset, gender)
                for dataset in self.DATASETS
                for gender in self.GENDERS
            ],
            "config": [
                self._config_candidates(dataset, gender)
                for dataset in self.DATASETS
                for gender in self.GENDERS
            ],
        }

    def _h5_candidates(self, dataset: str, gender: str) -> list[Path]:
        root = self.independent_dir / "base_store" / "saved_models" / dataset / gender
        return [root / "convolutional.h5", root / "model.h5"]

    def _tflite_candidates(self, dataset: str, gender: str) -> list[Path]:
        root = self.independent_dir / "base_store" / "saved_models" / dataset / gender
        return [root / "convolutional.tflite", root / "model.tflite"]

    def _config_candidates(self, dataset: str, gender: str) -> list[Path]:
        root = self.independent_dir / "base_store" / "saved_modelconfigs" / dataset / gender
        return [root / "convolutional", root / "config.pkl"]

    def _first_existing(self, paths: list[Path]) -> Path | None:
        return next((path for path in paths if path.exists()), None)

    def _available_slots(self, gender: str | None = None) -> list[tuple[str, str]]:
        slots: list[tuple[str, str]] = []
        genders = (gender,) if gender in self.GENDERS else self.GENDERS
        for dataset in self.DATASETS:
            for slot_gender in genders:
                if self._first_existing(self._h5_candidates(dataset, slot_gender)) and self._first_existing(
                    self._config_candidates(dataset, slot_gender)
                ):
                    slots.append((dataset, slot_gender))
        return slots

    def predict(self, audio_path: Path, gender: str = "male") -> BaselineResult:
        status = self.status()
        if self._available_slots(gender):
            try:
                return self._predict_with_available_models(audio_path, gender)
            except Exception as exc:
                return BaselineResult(
                    score=self._fallback_score(audio_path),
                    source="feature_fallback_after_upstream_error",
                    available=False,
                    details={**status, "error": str(exc)},
                )

        return BaselineResult(
            score=self._fallback_score(audio_path),
            source="feature_fallback_missing_upstream_models",
            available=False,
            details=status,
        )

    def _predict_with_available_models(self, audio_path: Path, gender: str) -> BaselineResult:
        root = str(self.repo_dir)
        if root not in sys.path:
            sys.path.insert(0, root)

        from backbone_independent.support import configurations_variables as confv
        from python_speech_features import mfcc

        signal, _ = librosa.load(str(audio_path), sr=confv.resample_rate)
        slots = self._available_slots(gender)
        slot_results = []
        for dataset, slot_gender in slots:
            model, config = self._load_h5_model_and_config(dataset, slot_gender)
            if hasattr(config, "feature_dim") and hasattr(config, "scaler"):
                vector = self._extract_fixed_vector(audio_path, int(config.feature_dim))
                vector = config.scaler.transform(vector.reshape(1, -1))
                mean_probs = model.predict(vector, verbose=0).flatten()
                labels = [str(label) for label in getattr(config, "class_names", [])]
                if not labels and hasattr(config, "label_encoder"):
                    labels = [str(label) for label in config.label_encoder.classes_]
                result = {labels[index]: float(mean_probs[index]) for index in range(min(len(labels), len(mean_probs)))}
            else:
                probs = []
                for start in range(0, signal.shape[0] - config.step, config.step):
                    sample = signal[start : start + config.step]
                    x = mfcc(sample, confv.resample_rate, numcep=config.nfeat, nfilt=config.nfilt, nfft=config.nfft)
                    denominator = config.max - config.min
                    if np.any(denominator == 0):
                        denominator = np.where(denominator == 0, 1.0, denominator)
                    x = (x - config.min) / denominator
                    x = x.reshape(1, x.shape[0], x.shape[1], 1)
                    probs.append(model.predict(x, verbose=0))
                if not probs:
                    continue
                mean_probs = np.mean(probs, axis=0).flatten()
                result = {config.classes[index]: float(mean_probs[index]) for index in range(len(config.classes))}
            slot_results.append({"dataset": dataset, "gender": slot_gender, "result": result})

        if not slot_results:
            raise RuntimeError("No usable external SER model produced probabilities.")

        score = float(np.mean([self._stress_score_from_ser_result(item["result"]) for item in slot_results]))
        return BaselineResult(
            score=float(np.clip(score, 0.0, 1.0)),
            source="isurusamarasekara_backbone_independent_h5",
            available=True,
            details={"gender": gender, "slots": slot_results},
        )

    def _extract_fixed_vector(self, audio_path: Path, feature_dim: int) -> np.ndarray:
        features = extract_audio_features(audio_path)
        if features.shape[0] == feature_dim:
            return features.astype(np.float32)
        if features.shape[0] > feature_dim:
            return features[:feature_dim].astype(np.float32)
        return np.pad(features, (0, feature_dim - features.shape[0])).astype(np.float32)

    @staticmethod
    def _stress_score_from_ser_result(result: dict[str, float]) -> float:
        if "Stressed" in result:
            return float(result.get("Stressed", 0.0))
        weights = {
            "angry": 1.0,
            "fearful": 0.95,
            "fear": 0.95,
            "sad": 0.75,
            "disgust": 0.7,
            "bored": 0.5,
            "boredom": 0.5,
            "surprised": 0.45,
            "neutral": 0.12,
            "calm": 0.08,
            "happy": 0.05,
        }
        total = sum(max(float(prob), 0.0) for prob in result.values())
        if total <= 0:
            return 0.0
        return float(
            np.clip(
                sum(max(float(prob), 0.0) * weights.get(label.lower(), 0.4) for label, prob in result.items()) / total,
                0.0,
                1.0,
            )
        )

    def _load_h5_model_and_config(self, dataset: str, gender: str) -> tuple[Any, Any]:
        key = (dataset, gender)
        if key in self._loaded_models:
            return self._loaded_models[key]

        from tensorflow.keras.models import load_model

        model_path = self._first_existing(self._h5_candidates(dataset, gender))
        config_path = self._first_existing(self._config_candidates(dataset, gender))
        if model_path is None or config_path is None:
            raise FileNotFoundError(f"Missing SER artifacts for {dataset}/{gender}")

        root = str(self.repo_dir)
        if root not in sys.path:
            sys.path.insert(0, root)
        from backbone_independent.support.configuration_classes import ModelConfig

        main_module = sys.modules.get("__main__")
        previous_model_config = getattr(main_module, "ModelConfig", None) if main_module else None
        if main_module is not None:
            setattr(main_module, "ModelConfig", ModelConfig)
        try:
            config = joblib.load(config_path)
        finally:
            if main_module is not None:
                if previous_model_config is None:
                    try:
                        delattr(main_module, "ModelConfig")
                    except AttributeError:
                        pass
                else:
                    setattr(main_module, "ModelConfig", previous_model_config)
        model = load_model(model_path, compile=False)
        self._loaded_models[key] = (model, config)
        return model, config

    @staticmethod
    def _fallback_score(audio_path: Path) -> float:
        features = extract_audio_features(audio_path)
        probs = NeuroGuardModels.heuristic_audio_probabilities(features)
        return float(np.clip(0.65 * probs[1] + probs[2], 0.0, 1.0))


class NeuroGuardStudentRuntime:
    def __init__(self, checkpoint_path: Path) -> None:
        self.checkpoint_path = checkpoint_path
        self._model = None
        self._config: dict[str, Any] = {}

    def predict(self, audio_path: Path, z_vector: list[float] | None = None) -> StudentResult:
        if self.checkpoint_path.exists():
            try:
                return self._predict_checkpoint(audio_path, z_vector)
            except Exception as exc:
                features = extract_audio_features(audio_path)
                probs = NeuroGuardModels.heuristic_audio_probabilities(features)
                return StudentResult(
                    score=float(np.clip(0.65 * probs[1] + probs[2], 0.0, 1.0)),
                    source=f"heuristic_after_student_error:{type(exc).__name__}",
                    probabilities=probs,
                )

        features = extract_audio_features(audio_path)
        probs = NeuroGuardModels.heuristic_audio_probabilities(features)
        return StudentResult(
            score=float(np.clip(0.65 * probs[1] + probs[2], 0.0, 1.0)),
            source="heuristic_missing_neuroguard_student_checkpoint",
            probabilities=probs,
        )

    def _load_model(self):
        if self._model is not None:
            return self._model

        import torch

        project_root = self.checkpoint_path.resolve().parents[2]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from training.student_model import NeuroGuardStudent

        checkpoint = torch.load(self.checkpoint_path, map_location="cpu")
        config = checkpoint.get("model_config", {})
        model = NeuroGuardStudent(**config)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        self._config = config
        self._model = model
        return model

    def _predict_checkpoint(self, audio_path: Path, z_vector: list[float] | None) -> StudentResult:
        import torch

        model = self._load_model()
        log_mel = self._log_mel_tensor(audio_path)
        z_tensor = None
        if z_vector:
            z_dim = int(self._config.get("z_dim", 48))
            values = np.asarray(z_vector[:z_dim], dtype=np.float32)
            if values.shape[0] < z_dim:
                values = np.pad(values, (0, z_dim - values.shape[0]))
            z_tensor = torch.tensor(values, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            logits = model(log_mel, z_vector=z_tensor)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
        score = float(np.clip(0.65 * probs[1] + probs[2], 0.0, 1.0))
        return StudentResult(
            score=score,
            source="neuroguard_audio_student_checkpoint",
            probabilities=probs,
        )

    @staticmethod
    def _log_mel_tensor(audio_path: Path):
        import torch

        y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
        mel = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=400,
            hop_length=160,
            n_mels=64,
            power=2.0,
        )
        log_mel = librosa.power_to_db(mel).astype(np.float32)
        return torch.tensor(log_mel, dtype=torch.float32).unsqueeze(0)


class StressVoicePipeline:
    def __init__(
        self,
        external_repo_dir: Path,
        student_checkpoint_path: Path,
        baseline_weight: float = 0.2,
        orchestrator: AdaptiveWeightingEngine | None = None,
    ) -> None:
        self.external = ExternalStressBackbone(external_repo_dir)
        self.student = NeuroGuardStudentRuntime(student_checkpoint_path)
        self.baseline_weight = float(np.clip(baseline_weight, 0.0, 1.0))
        self.orchestrator = orchestrator or AdaptiveWeightingEngine()

    def status(self) -> dict[str, Any]:
        return {
            "external_backbone": self.external.status(),
            "student_checkpoint": {
                "path": str(self.student.checkpoint_path),
                "exists": self.student.checkpoint_path.exists(),
            },
            "baseline_weight": self.baseline_weight,
        }

    def predict(
        self,
        audio_path: Path,
        z_vector: list[float] | None = None,
        gender: str = "male",
        baseline_weight: float | None = None,
        student_id: str | None = None,
    ) -> StressVoiceResult:
        baseline = self.external.predict(audio_path, gender=gender)
        student = self.student.predict(audio_path, z_vector=z_vector)
        orchestration = self.orchestrator.combine(
            baseline=baseline.score,
            neuroguard=student.score,
            student_id=student_id,
            baseline_weight_override=baseline_weight,
        )
        probs = probabilities_from_stress_score(orchestration.final_stress)
        prediction = int(np.argmax(probs))
        confidence = float(probs[prediction])
        return StressVoiceResult(
            baseline=baseline,
            student=student,
            final_stress=orchestration.final_stress,
            probabilities=probs,
            prediction=prediction,
            confidence=confidence,
            orchestration=orchestration,
        )
