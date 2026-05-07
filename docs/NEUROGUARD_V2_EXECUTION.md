# NeuroGuard v2 Execution Checklist

## Week 0: Prerequisites

- Python 3.10 environment for backend/ML.
- Node 20+ for Next.js, Hardhat, SnarkJS.
- Supabase project with `supabase/schema.sql` applied.
- Polygon Amoy wallet funded with test POL.
- Optional: `flwr`, `torch`, `torchaudio`, `transformers`, `circom`, `snarkjs`.

## Week 1: Data Factory and Personalization

- Generate or collect Hinglish prompts in `data_factory/prompts_hinglish.txt`.
- Build a synthetic manifest with `python data_factory/generate_manifest.py`.
- Use `/enrolments/voice` to create a per-student `z_vector`.
- Store enrolment vectors in `voice_enrolments`; store hashes instead of raw audio by default.

## Option B: Knowledge Distillation

Option B is approved for NeuroGuard v2 and is the preferred training design.

```text
FunAudioLLM/SenseVoiceSmall teacher
        -> soft SER guidance during training only
NeuroGuard student model
        -> final personalized stress score at runtime
```

- SenseVoiceSmall is frozen and offline.
- NeuroGuard remains the final decision-maker.
- The deployed FastAPI path does not call the teacher.
- The per-student `z_vector` still changes the final stress score, so personalization is preserved.
- Use `training/train_distillation.py` to train the student model with CE + KL distillation loss.

Training command:

```powershell
pip install -r training/requirements.txt
python -m training.train_distillation --manifest data_factory/manifest.csv
```

Development check without downloading SenseVoice:

```powershell
python -m training.train_distillation --manifest data_factory/manifest.csv --disable-teacher
```

Do not use `nvidia/Audio2Emotion-v3.0` for this app because its license blocks standalone emotion-recognition use outside Audio2Face.

## Week 2: ZK-FL

- Simulate five college clients with `python fl/simulate_fedavg.py`.
- Compile `circuits/local_train.circom` and `circuits/aggregation.circom`.
- Treat circuit outputs as proof hashes in the current backend audit flow.
- Replace compact demo proofs with Merkle-committed model tensors for production.

## Section 6: Voice-Stress-Detection Backbone Integration

### Objective

Replace the placeholder-tone-based voice training path with a real-speech stress-detection backbone from an existing GitHub project, while preserving NeuroGuard v2 personalization, consent, Supabase storage, ZK-FL scaffolding, and Polygon audit features.

Detailed Windows/no-hardware PRD: `docs/WINDOWS_REALTIME_SER_PRD.md`.

### 6.1 Why This Change Is Needed

- `backend/models/neuroguard_audio_student.pt` proves the Option B training pipeline works, but it was trained on generated placeholder tones.
- Placeholder tones do not represent real student speech, Hinglish code-mixing, or stress-related vocal patterns.
- The TTS data factory should pause until it can produce meaningful, emotion-labelled student-style speech.
- NeuroGuard now pivots to a real-speech GitHub backbone as a baseline signal while keeping the NeuroGuard personalized head on top.

### 6.2 Selected GitHub Project

- Repo: `isurusamarasekara/Stress-Detection-Through-Speech-Emotion-Recognition`
- GitHub: https://github.com/isurusamarasekara/Stress-Detection-Through-Speech-Emotion-Recognition
- License: MIT
- Local clone: `third_party/Stress-Detection-Through-Speech-Emotion-Recognition`

The repo includes:

- `backbone/`: research/training pipeline.
- `backbone_independent/`: Windows-oriented prediction flow.
- `speech_analysis_raspi/`: Raspberry-Pi-style speech prediction scripts.

Important practical note: the upstream README says trained audio folders, saved model configs, saved models, logs, features, and metrics are not pushed because they are large. Because of that, NeuroGuard cannot run the upstream `backbone_independent` model path until those model assets are supplied.

### 6.3 Architecture After Integration

```text
Raw audio
  ↓
[External GitHub backbone adapter] -> stress_baseline
  ↓
[NeuroGuard audio student + z_vector] -> stress_neuroguard
  ↓
[Weighted final score] -> final_stress
  ↓
[Supabase + audit_events + ZK-FL/Polygon hooks]
```

Current weighted score:

```python
final_stress = 0.2 * stress_baseline + 0.8 * stress_neuroguard
```

This can be changed with `STRESS_BASELINE_WEIGHT`.

### 6.4 Implemented FastAPI Route

Implemented route:

```text
POST /predict/stress_voice
```

Inputs:

- `audio`: uploaded WAV/audio clip.
- `student_id`: optional student id for saving and `z_vector` lookup.
- `save`: whether to save prediction/audio metadata.
- `gender`: passed to the upstream adapter when upstream model files are present.
- `baseline_weight`: optional per-request override.

Outputs:

- `stress_baseline`
- `stress_neuroguard`
- `final_stress`
- `baseline_source`
- `neuroguard_source`
- `baseline_available`
- class probabilities
- audit metadata

### 6.5 Current Runtime Behavior

If upstream TFLite/modelconfig files exist:

```text
baseline_source = isurusamarasekara_backbone_independent_h5
baseline_available = true
```

If upstream model files are missing:

```text
baseline_source = feature_fallback_missing_upstream_models
baseline_available = false
```

The route still works in fallback mode so frontend/backend integration can be tested now. For final evaluation, add the upstream model assets or retrain them from the upstream `backbone/` pipeline. The current upstream `backbone_independent/support/predict.py` loads `convolutional.h5`; the PRD also tracks `convolutional.tflite` artifacts because the training flow can export them.

### 6.6 Files Added/Updated

- `backend/app/services/stress_voice_service.py`
- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/app/core/config.py`
- `frontend/src/components/audio-recorder.tsx`
- `frontend/src/lib/api.ts`
- `supabase/schema.sql`

### 6.7 Immediate Next Steps

- Add or train the missing upstream TFLite/modelconfig assets under:

```text
third_party/Stress-Detection-Through-Speech-Emotion-Recognition/backbone_independent/base_store/
```

- Test `/predict/stress_voice` with real neutral and stressed speech clips.
- Replace generated placeholder WAVs with real/TTS Hinglish samples.
- Decide long-term direction:
  - keep weighted ensemble,
  - switch to the GitHub backbone with NeuroGuard head,
  - or use the GitHub backbone as an offline distillation teacher.

## Week 3: Full Stack and Contracts

- Deploy `contracts/contracts/ConsentDAO.sol` and `contracts/contracts/Audit.sol` to Polygon Amoy.
- Configure:

```text
POLYGON_AMOY_RPC_URL=
PRIVATE_KEY=
CONSENT_CONTRACT_ADDRESS=
AUDIT_CONTRACT_ADDRESS=
```

- Backend currently records audit hashes in Supabase; contract transaction submission is the next integration step.

## Week 4: Testing and Demo

- Run backend health and frontend build.
- Demo flow:
  `login -> voice enrolment -> survey/audio prediction -> Supabase save -> high-risk audit event -> counsellor dashboard`.
- Use `prediction_class = 2` or `risk_level = high` as the alert trigger.

## Current Implementation Status

- Existing PDS tabular/fusion/LSTM app preserved.
- Audio route now works with either trained audio model or deterministic heuristic fallback.
- Voice enrolment API and UI added.
- Consent, voice enrolment, and audit Supabase tables added.
- Smart contract, ZK circuit, FL, and data-factory scaffolds added.
