from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

import torch
import soundfile as sf


STRESS_CLASS_COUNT = 3


EMOTION_PRIORS = {
    "neutral": [0.86, 0.12, 0.02],
    "happy": [0.78, 0.18, 0.04],
    "sad": [0.14, 0.62, 0.24],
    "angry": [0.06, 0.58, 0.36],
    "fear": [0.04, 0.46, 0.50],
    "disgust": [0.08, 0.55, 0.37],
    "surprise": [0.42, 0.46, 0.12],
}


@dataclass(frozen=True)
class TeacherOutput:
    logits: torch.Tensor
    raw_text: str
    emotion: str


class SenseVoiceTeacher:
    """Frozen offline SER teacher for Option B distillation.

    SenseVoice usually returns rich transcription tags rather than a simple
    HuggingFace `logits` tensor. For the project pipeline we convert the
    detected emotion tag into calibrated stress-class soft logits. This keeps
    the teacher offline and replaceable while the NeuroGuard student remains
    the only deployed model.
    """

    def __init__(
        self,
        model_dir: str = "FunAudioLLM/SenseVoiceSmall",
        device: str = "cpu",
        enabled: bool = True,
    ) -> None:
        self.model_dir = model_dir
        self.device = device
        self.enabled = enabled
        self._model = None
        if enabled:
            self._load()

    def _load(self) -> None:
        try:
            import imageio_ffmpeg
            from funasr import AutoModel
        except ImportError as exc:
            raise RuntimeError(
                "SenseVoice teacher requires optional training dependencies. "
                "Install them with: pip install -r training/requirements.txt"
            ) from exc

        os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

        self._model = AutoModel(
            model=self.model_dir,
            device=self.device,
            hub="hf",
            trust_remote_code=True,
            disable_update=True,
        )

    @staticmethod
    def _emotion_from_text(text: str) -> str:
        lowered = text.lower()
        for emotion in EMOTION_PRIORS:
            if emotion in lowered:
                return emotion
        if "angry" in lowered or "anger" in lowered:
            return "angry"
        if "sad" in lowered:
            return "sad"
        return "neutral"

    @staticmethod
    def _logits_for_emotion(emotion: str) -> torch.Tensor:
        prior = torch.tensor(EMOTION_PRIORS.get(emotion, EMOTION_PRIORS["neutral"]), dtype=torch.float32)
        return torch.log(prior.clamp_min(1e-6))

    def predict_one(self, audio_path: str | Path) -> TeacherOutput:
        if not self.enabled:
            logits = torch.log(torch.tensor([0.34, 0.33, 0.33], dtype=torch.float32))
            return TeacherOutput(logits=logits, raw_text="teacher_disabled", emotion="neutral")

        if self._model is None:
            self._load()

        waveform, sample_rate = sf.read(str(audio_path), dtype="float32")
        if getattr(waveform, "ndim", 1) == 2:
            waveform = waveform.mean(axis=1)

        result = self._model.generate(
            input=waveform,
            cache={},
            language="auto",
            use_itn=True,
            batch_size_s=60,
            fs=sample_rate,
        )
        raw_text = str(result[0].get("text", "")) if result else ""
        emotion = self._emotion_from_text(raw_text)
        return TeacherOutput(
            logits=self._logits_for_emotion(emotion),
            raw_text=raw_text,
            emotion=emotion,
        )

    def predict_batch(self, audio_paths: Iterable[str | Path]) -> torch.Tensor:
        logits = [self.predict_one(path).logits for path in audio_paths]
        return torch.stack(logits, dim=0)
