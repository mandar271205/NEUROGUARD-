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

    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
    mfcc_mean = np.mean(mfccs, axis=1)
    mfcc_std = np.std(mfccs, axis=1)
    
    chroma = np.mean(librosa.feature.chroma_stft(y=y, sr=sr), axis=1)
    mel = np.mean(librosa.feature.melspectrogram(y=y, sr=sr), axis=1)[:20]
    contrast = np.mean(librosa.feature.spectral_contrast(y=y, sr=sr), axis=1)

    f0, _, _ = librosa.pyin(y, fmin=50, fmax=400)
    f0_clean = f0[~np.isnan(f0)] if f0 is not None and len(f0[~np.isnan(f0)]) > 0 else np.array([0.0])
    pitch_mean = np.mean(f0_clean)
    pitch_std = np.std(f0_clean)

    rms = librosa.feature.rms(y=y)[0]
    shimmer = np.std(rms) / (np.mean(rms) + 1e-8)
    zcr = np.mean(librosa.feature.zero_crossing_rate(y=y)[0])
    centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))

    features = np.concatenate([
        mfcc_mean, 
        mfcc_std, 
        chroma, 
        mel, 
        contrast, 
        [pitch_mean, pitch_std, shimmer, zcr, centroid]
    ]).astype(np.float32)

    return features
