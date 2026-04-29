from pathlib import Path

import librosa
import numpy as np


def _safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) < 1e-9:
        return 0.0
    return float(numerator / denominator)


def extract_audio_features(audio_path: Path, sample_rate: int = 22050) -> np.ndarray:
    y, sr = librosa.load(str(audio_path), sr=sample_rate, mono=True)
    if y.size == 0:
        raise ValueError("Audio file is empty.")

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
    mfcc_mean = mfcc.mean(axis=1)
    mfcc_std = mfcc.std(axis=1)

    f0 = librosa.yin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        sr=sr,
    )
    f0 = f0[np.isfinite(f0)]
    pitch_mean = float(np.mean(f0)) if f0.size else 0.0
    pitch_std = float(np.std(f0)) if f0.size else 0.0

    rms = librosa.feature.rms(y=y)[0]
    shimmer = _safe_ratio(float(np.mean(np.abs(np.diff(rms)))) if rms.size > 1 else 0.0, float(np.mean(rms)))
    jitter = _safe_ratio(float(np.mean(np.abs(np.diff(f0)))) if f0.size > 1 else 0.0, pitch_mean)
    spectral_centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())

    features = np.concatenate(
        [
            mfcc_mean,
            mfcc_std,
            np.array([pitch_mean, pitch_std, shimmer, jitter, spectral_centroid]),
        ]
    ).astype(np.float32)

    if features.shape[0] != 85:
        raise ValueError(f"Expected 85 audio features, got {features.shape[0]}.")
    return features
