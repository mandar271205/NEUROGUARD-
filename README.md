# NeuroGuard v2

[![Frontend](https://img.shields.io/badge/Frontend-Next.js-111827?style=for-the-badge&logo=nextdotjs)](https://nextjs.org/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/Database-Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=0f172a)](https://supabase.com/)
[![ML](https://img.shields.io/badge/ML-RF%20%7C%20LSTM%20%7C%20SER%20%7C%20AAMO-245F9D?style=for-the-badge)](#machine-learning-stack)

NeuroGuard v2 is a student mental-health early-warning platform that combines survey-based machine learning, speech emotion recognition, personalized voice enrolment, adaptive model orchestration, counsellor alerts, Supabase audit storage, and blockchain/ZK-FL scaffolding.

The system classifies student stress into:

| Class | Label | Meaning |
| --- | --- | --- |
| `0` | Normal | Low immediate concern |
| `1` | High-Stress | Elevated stress indicators |
| `2` | High-Risk | Needs counsellor attention |

Project context: Python for Data Science final project, Sardar Patel Institute of Technology, Mumbai.

## What Is New In v2

- Real voice-stress pipeline through `POST /predict/stress_voice`.
- External SER backbone from `isurusamarasekara/Stress-Detection-Through-Speech-Emotion-Recognition`.
- Runtime voice artifacts for RAVDESS, CREMA-D, and EmoDB are included under `third_party/.../backbone_independent/base_store/`.
- NeuroGuard student audio model at `backend/models/neuroguard_audio_student.pt`.
- Voice enrolment endpoint and UI that creates a per-student `z_vector`.
- Auto-Adaptive Model Orchestrator (AAMO) that dynamically weights external baseline vs NeuroGuard student output.
- Polished Next.js UI for login, dashboard, survey, audio recorder, enrolment, counsellor review, and alerts.
- AudioWorklet-based browser recorder, replacing deprecated `ScriptProcessorNode`.
- Distillation training path using SenseVoiceSmall as an offline teacher.
- Supabase schema additions for voice enrolment, consent logs, predictions, and audit events.
- Circom and Polygon contract scaffolding for verifiable FL/audit workflows.

## High-Level Architecture

```text
Student / Counsellor Browser
          |
          v
Next.js Frontend  <------ Supabase Auth + Realtime
          |
          v
FastAPI Backend
          |
          +--> Survey Random Forest
          +--> Temporal LSTM
          +--> Fusion Gradient Boosting
          +--> External SER Backbone
          +--> NeuroGuard Audio Student
          +--> AAMO Adaptive Orchestrator
          |
          v
Supabase PostgreSQL + Audit Events
          |
          v
Polygon / ZK-FL scaffolding
```

## Voice Stress Pipeline

```text
Raw browser microphone audio
  |
  v
External SER Backbone
  -> stress_baseline

NeuroGuard Audio Student + student z_vector
  -> stress_neuroguard

AAMO
  -> dynamic weights
  -> final_stress
  -> risk_level
  -> Supabase prediction/audit log
```

The current combined score is not a fixed `0.2/0.8` blend. AAMO watches recent prediction behaviour and adapts:

- Cold start: baseline gets more weight while there is not enough history.
- Flat NeuroGuard output: baseline is trusted more.
- Healthy NeuroGuard variation: NeuroGuard weight increases.
- API response includes weights and health scores for transparency.

Example response fields:

```json
{
  "stress_baseline": 0.73,
  "stress_neuroguard": 0.50,
  "final_stress": 0.66,
  "weight_baseline": 0.70,
  "weight_neuroguard": 0.30,
  "health_baseline": 0.0,
  "health_neuroguard": 0.0,
  "orchestrator_mode": "cold_start"
}
```

## Repository Structure

```text
.
+-- backend/
|   +-- app/
|   |   +-- core/                         # config and auth helpers
|   |   +-- services/
|   |   |   +-- model_service.py          # survey, fusion, temporal, legacy audio
|   |   |   +-- stress_voice_service.py   # external SER + NeuroGuard voice pipeline
|   |   |   +-- adaptive_orchestrator.py  # AAMO dynamic weighting
|   |   |   +-- supabase_service.py       # persistence and audit
|   |   +-- main.py                       # FastAPI routes
|   |   +-- schemas.py
|   +-- models/
|   |   +-- neuroguard_audio_student.pt
|   +-- requirements.txt
+-- frontend/
|   +-- public/audio-recorder-worklet.js
|   +-- src/app/                          # Next.js App Router pages
|   +-- src/components/                   # shell, dashboards, recorder, forms
|   +-- src/lib/                          # API, Supabase, schema
+-- PDS MODEL 2/                          # original trained PDS model artifacts
+-- third_party/
|   +-- Stress-Detection-Through-Speech-Emotion-Recognition/
|       +-- backbone_independent/         # trimmed Windows-ready SER inference module
|           +-- base_store/               # included RAVDESS/CREMA-D/EmoDB artifacts
+-- training/                             # Option B distillation pipeline
+-- data_factory/                         # Hinglish prompt manifest tooling
+-- supabase/schema.sql                   # tables, RLS, realtime publication
+-- contracts/                            # ConsentDAO and Audit contracts
+-- circuits/                             # Circom proof scaffolds
+-- fl/                                   # FedAvg simulation
+-- docs/                                 # execution PRDs and implementation notes
```

## Machine Learning Stack

| Layer | File / Module | Purpose |
| --- | --- | --- |
| Survey Random Forest | `PDS MODEL 2/neuroguard_rf.pkl` | Predicts stress from 20 survey answers plus engineered features |
| Temporal LSTM | `PDS MODEL 2/neuroguard_lstm.keras` | Demonstrates longitudinal stress prediction |
| Fusion Gradient Boosting | `PDS MODEL 2/neuroguard_fusion.pkl` | Combines multimodal probabilities |
| Legacy Audio MLP | `PDS MODEL 2/neuroguard_audio.keras` when present | Older audio pathway or fallback support |
| External SER Backbone | `third_party/.../backbone_independent/` | Real-speech emotion/stress baseline from MFCC/ZCR/RMS/chroma features |
| NeuroGuard Audio Student | `backend/models/neuroguard_audio_student.pt` | Own deployed personalized voice model |
| AAMO | `backend/app/services/adaptive_orchestrator.py` | Dynamically combines baseline and NeuroGuard voice scores |
| SenseVoice Teacher | `training/teacher_sensevoice.py` | Optional offline teacher for distillation training |

Active external SER slots:

- RAVDESS female/male
- CREMA-D female/male
- EmoDB female/male

ShEMO is intentionally not active because the available training split was too small for a reliable model artifact in this project state.

## Frontend Features

### Student Portal

- Student sign in and sign up.
- Survey form with probability chart and AI justification.
- Student dashboard with latest risk, trend chart, privacy/audit status, and quick actions.
- Voice enrolment page for personalization vector creation.
- Audio recorder that records in-browser WAV clips using AudioWorklet.
- Combined voice stress results with baseline score, NeuroGuard score, AAMO weights, and final stress.

### Counsellor Portal

- Counsellor-only sign in flow.
- Assigned student list.
- Search/filter student records.
- Student detail timeline.
- Supabase realtime high-risk alert panel.

### UI/UX

- Clean product-style layout with sidebar navigation.
- Responsive mobile header.
- Polished cards, metric tiles, input states, and result panels.
- Demo-ready audio recorder screen for PPT/research presentation screenshots.

## Backend API

Core routes:

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Model and service health |
| `POST` | `/predict/tabular` | Survey Random Forest prediction |
| `POST` | `/predict/audio` | Legacy audio prediction path |
| `POST` | `/predict/full` | Fusion prediction |
| `POST` | `/predict/temporal` | Temporal LSTM prediction |
| `POST` | `/predict/stress_voice` | Combined external SER + NeuroGuard + AAMO voice prediction |
| `POST` | `/enrolments/voice` | Create per-student voice `z_vector` |
| `POST` | `/students/me` | Ensure logged-in student profile |
| `GET` | `/students` | Counsellor student list |
| `GET` | `/students/{id}/history` | Student history |
| `POST` | `/surveys` | Save survey |
| `POST` | `/audio/upload` | Save uploaded audio metadata |
| `POST` | `/consent` | Store consent log |

Expected `/health` model flags in the current local setup:

```json
{
  "tabular_rf": true,
  "fusion_gb": true,
  "audio_mlp": true,
  "temporal_lstm": true,
  "stress_voice_combined": true,
  "external_stress_backbone": true,
  "neuroguard_audio_student": true
}
```

## Option B: Knowledge Distillation

Option B is the recommended long-term training path:

```text
SenseVoiceSmall teacher
  -> soft SER labels
  -> NeuroGuard student model + z_vector conditioning
  -> deployed personalized stress model
```

The teacher is used offline during training only. Runtime inference serves only the NeuroGuard model and the local external backbone adapter.

```powershell
pip install -r training/requirements.txt
python -m training.train_distillation --manifest data_factory/manifest.csv
```

See:

- `docs/OPTION_B_DISTILLATION_PRD.md`
- `training/README.md`

## External SER Backbone

The integrated backbone is based on:

```text
isurusamarasekara/Stress-Detection-Through-Speech-Emotion-Recognition
```

Local path:

```text
third_party/Stress-Detection-Through-Speech-Emotion-Recognition
```

Only the lightweight `backbone_independent/` inference module and required runtime artifacts are kept. Raw datasets and heavy training/download folders are not committed.

See `docs/WINDOWS_REALTIME_SER_PRD.md` for the Windows real-time microphone PRD and artifact checklist.

## Supabase Setup

1. Create a Supabase project.
2. Run `supabase/schema.sql` in the Supabase SQL editor.
3. Enable email/password authentication.
4. Add frontend and backend environment values.
5. For counsellors, create users in Supabase Auth and set metadata:

```json
{
  "role": "counsellor"
}
```

6. Assign students to counsellors by setting `students.counsellor_id` to the counsellor auth user id.

Student accounts created from the app are connected to backend student profiles through `POST /students/me`.

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Set `backend/.env`:

```text
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_AUDIENCE=authenticated
API_CORS_ORIGINS=http://localhost:3000
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Frontend Setup

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Set `frontend/.env.local`:

```text
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Open:

```text
http://localhost:3000
```

## Validation Completed

Latest local checks:

- `python -m compileall backend\app` passed.
- `npm run lint` passed.
- `npm run build` passed.
- FastAPI `/health` loads the survey, temporal, fusion, external SER, and NeuroGuard audio student flags.
- `POST /predict/stress_voice` works with the included external SER artifacts and NeuroGuard student checkpoint.
- Frontend `/audio` loads successfully.
- `frontend/public/audio-recorder-worklet.js` is served successfully.

## Deployment Notes

### Frontend

Deploy `frontend/` to Vercel and set:

```text
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_API_BASE_URL
```

### Backend

Deploy `backend/` to Render, Railway, or another Python/Docker host. Include model files and set:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_AUDIENCE
API_CORS_ORIGINS
MODEL_DIR=/app/models
```

## Research / PPT Summary

NeuroGuard v2 is a multimodal stress-detection platform for students. It uses:

1. Survey ML for structured psychometric signals.
2. Speech emotion recognition for real voice stress indicators.
3. Per-student voice enrolment for personalization.
4. AAMO for adaptive score fusion when one model is flat or unreliable.
5. Supabase and realtime alerts for counsellor workflows.
6. ZK-FL and blockchain scaffolding for future privacy-preserving verification.

Core contribution: instead of relying on one fixed model, NeuroGuard v2 uses a model-orchestration layer that monitors model behaviour and dynamically chooses how much to trust each voice model per prediction window.

## References

- FastAPI documentation.
- Supabase documentation.
- Next.js documentation.
- RAVDESS dataset.
- CREMA-D dataset.
- EmoDB dataset.
- `isurusamarasekara/Stress-Detection-Through-Speech-Emotion-Recognition`.
- SenseVoice / FunAudioLLM model family for optional offline distillation.

## Team

Course: Python for Data Science

Institution: Sardar Patel Institute of Technology, Mumbai

Project: NeuroGuard v2, a multimodal early-warning system for student mental-health risk.
