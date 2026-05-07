from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
import soundfile as sf
import torchaudio
from torch.utils.data import Dataset


LABEL_TO_ID = {
    "normal": 0,
    "neutral": 0,
    "low": 0,
    "stress": 1,
    "high-stress": 1,
    "moderate": 1,
    "high_risk": 2,
    "high-risk": 2,
    "risk": 2,
}


class SpeechManifestDataset(Dataset):
    def __init__(
        self,
        manifest_path: str | Path,
        sample_rate: int = 16000,
        n_mels: int = 64,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.root = self.manifest_path.parent.parent
        self.sample_rate = sample_rate
        self.rows = self._load_rows()
        self.mel = torchaudio.transforms.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=400,
            hop_length=160,
            n_mels=n_mels,
        )
        self.to_db = torchaudio.transforms.AmplitudeToDB()

    def _load_rows(self) -> list[dict[str, str]]:
        with self.manifest_path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def __len__(self) -> int:
        return len(self.rows)

    def _resolve_audio_path(self, file_path: str) -> Path:
        path = Path(file_path)
        if path.is_absolute():
            return path
        return (self.root / path).resolve()

    def __getitem__(self, index: int) -> dict[str, Any]:
        row = self.rows[index]
        audio_path = self._resolve_audio_path(row["file_path"])
        audio, sr = sf.read(str(audio_path), dtype="float32")
        waveform = torch.from_numpy(audio).float()
        if waveform.ndim == 2:
            waveform = waveform.mean(dim=1)
        waveform = waveform.unsqueeze(0)
        if sr != self.sample_rate:
            waveform = torchaudio.functional.resample(waveform, sr, self.sample_rate)

        log_mel = self.to_db(self.mel(waveform)).squeeze(0)
        label_name = row.get("label", "neutral").lower().strip()
        label = LABEL_TO_ID.get(label_name, 0)
        return {
            "audio_path": str(audio_path),
            "log_mel": log_mel,
            "label": torch.tensor(label, dtype=torch.long),
        }


def collate_speech_batch(batch: list[dict[str, Any]]) -> dict[str, Any]:
    max_frames = max(item["log_mel"].shape[-1] for item in batch)
    padded = [
        F.pad(item["log_mel"], (0, max_frames - item["log_mel"].shape[-1]))
        for item in batch
    ]
    return {
        "audio_paths": [item["audio_path"] for item in batch],
        "log_mel": torch.stack(padded, dim=0),
        "labels": torch.stack([item["label"] for item in batch], dim=0),
    }
