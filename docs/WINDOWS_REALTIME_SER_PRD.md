# PRD: Stress Detection via Speech Emotion Recognition

## Real-Time Microphone Prediction - Windows

| Field | Value |
| --- | --- |
| Version | 1.0 |
| Status | Draft |
| Module | `backbone_independent/` |
| Platform | Windows 10/11, no Raspberry Pi or external hardware |
| Author | Mandar |
| Date | May 2026 |

## 1. Project Overview

This PRD covers running real-time stress detection from a laptop/desktop microphone on Windows with no external hardware. The system uses the `backbone_independent/` module from `isurusamarasekara/Stress-Detection-Through-Speech-Emotion-Recognition`.

Audio is captured from the system mic in streaming chunks. MFCC and related vocal features are extracted per chunk. Trained gender-split models output stress level in near real time.

| Item | Requirement |
| --- | --- |
| Repo module | `backbone_independent/` |
| Entry point | `mains-predictions/main_real_time.py` |
| Input | Windows system microphone |
| Output | Console stress level per audio chunk |
| Hardware | No Raspberry Pi required |
| Required artifacts | trained model files + modelconfig files from `backbone/` |

## 2. Scope

In scope:

- Train eight gender-split emotion models using `backbone/`.
- Copy trained artifacts into `backbone_independent/base_store/`.
- Run `main_real_time.py` on Windows for live mic stress prediction.
- Optionally run `main_prerecorded_upload.py` for file-based testing.
- Integrate the artifact-backed baseline into NeuroGuard `/predict/stress_voice`.

Out of scope:

- Raspberry Pi deployment.
- GUI for the standalone script.
- Cloud training.

## 3. System Flow

| Phase | Module | Description |
| --- | --- | --- |
| 1A | `backbone/` | Download datasets, extract features, train gender/dataset models, save artifacts |
| 1B | manual | Copy `saved_models/` and `saved_modelconfigs/` into `backbone_independent/base_store/` |
| 2 | `backbone_independent/` | Mic chunks -> feature extraction -> model inference -> stress output |
| 3 | NeuroGuard | `/predict/stress_voice` combines baseline + NeuroGuard personalized score |

## 4. Environment Setup

Use Python 3.8 or 3.9 for the standalone upstream scripts because older TFLite/runtime stacks can be brittle on newer Windows Python versions.

```powershell
python -m venv venv_ser
.\venv_ser\Scripts\Activate.ps1
pip install -r requirements.txt
```

Useful mic check:

```powershell
python -c "import sounddevice as sd; print(sd.query_devices())"
```

## 5. Training Artifacts

Download and gender-split:

| Dataset | Target folders |
| --- | --- |
| RAVDESS | `clean_audio/ravdess_f/`, `clean_audio/ravdess_m/` |
| CREMA-D | `clean_audio/cremad_f/`, `clean_audio/cremad_m/` |
| EmoDB | `clean_audio/emodb_f/`, `clean_audio/emodb_m/` |
| ShEMO | `clean_audio/shemo_f/`, `clean_audio/shemo_m/` |

Run:

```powershell
cd backbone
python mains-dataset_wise_structural/main_ravdess_female.py
python mains-dataset_wise_structural/main_ravdess_male.py
python mains-dataset_wise_structural/main_cremad_female.py
python mains-dataset_wise_structural/main_cremad_male.py
python mains-dataset_wise_structural/main_emodb_female.py
python mains-dataset_wise_structural/main_emodb_male.py
python mains-dataset_wise_structural/main_shemo_female.py
python mains-dataset_wise_structural/main_shemo_male.py
```

Expected output slots:

```text
backbone/base_store/saved_models/{dataset}/{gender}/convolutional.h5
backbone/base_store/saved_models/{dataset}/{gender}/convolutional.tflite
backbone/base_store/saved_modelconfigs/{dataset}/{gender}/convolutional
```

## 6. Copy Into `backbone_independent/`

```powershell
Copy-Item -Recurse backbone\base_store\saved_models\* `
  backbone_independent\base_store\saved_models\

Copy-Item -Recurse backbone\base_store\saved_modelconfigs\* `
  backbone_independent\base_store\saved_modelconfigs\
```

NeuroGuard checks these expected locations under:

```text
third_party/Stress-Detection-Through-Speech-Emotion-Recognition/backbone_independent/base_store/
```

## 7. Real-Time Script

```powershell
cd backbone_independent
python mains-predictions/main_real_time.py
```

Expected console pattern:

```text
[00:03] Predicted emotion: angry -> Stress: HIGH
[00:06] Predicted emotion: neutral -> Stress: LOW
```

## 8. NeuroGuard Integration

NeuroGuard exposes:

```text
POST /predict/stress_voice
```

Current behavior:

- If `backbone_independent` artifacts exist, use upstream baseline via `backbone_independent.support.predict.predict_upload`.
- If artifacts are missing, use feature fallback and report `baseline_available=false`.
- Always combine with the NeuroGuard personalized student checkpoint when available.

Blend:

```python
final_stress = 0.2 * stress_baseline + 0.8 * stress_neuroguard
```

## 9. Acceptance Criteria

| Criterion | Pass condition |
| --- | --- |
| Eight model slots present | `h5_model_count == 8` or `tflite_model_count == 8` |
| Eight config slots present | `model_config_count == 8` |
| NeuroGuard route works | `/predict/stress_voice` returns 200 |
| Missing artifacts do not crash app | route returns fallback score |
| Frontend works | `/audio` records/uploads and displays combined result |

## 10. Current Status

- Repo cloned.
- NeuroGuard adapter implemented against `backbone_independent/`.
- Upstream trained artifacts are currently missing.
- Website remains working through fallback + NeuroGuard student checkpoint.
