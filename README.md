# NeuroGuard

[![Frontend](https://img.shields.io/badge/Frontend-Next.js-111827?style=for-the-badge&logo=nextdotjs)](https://nextjs.org/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/Database-Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=0f172a)](https://supabase.com/)
[![ML](https://img.shields.io/badge/ML-RF%20%7C%20LSTM%20%7C%20Fusion-2B6CB0?style=for-the-badge)](#machine-learning)

NeuroGuard is a student mental health early-warning system. The current `PDS MODEL 2` package combines psychometric survey signals, a temporal LSTM demonstration, and late-fusion machine learning to classify stress into:

| Class | Label | Meaning |
| --- | --- | --- |
| `0` | Normal | Low immediate concern |
| `1` | High-Stress | Elevated stress indicators |
| `2` | High-Risk | Needs counsellor attention |

The project was built for the Python for Data Science final project at Sardar Patel Institute of Technology, Mumbai.

## Highlights

- Separate Student Sign in, Student Sign up, and Counsellor Sign in flows.
- Student portal with survey form, RF probability chart, temporal LSTM result, and risk dashboard.
- Counsellor portal with assigned student list, risk flags, history view, and realtime high-risk alerts.
- FastAPI backend that loads the trained Google Colab model artifacts directly from the project folder.
- Supabase Auth, PostgreSQL, Row Level Security, and Realtime events.
- Local-first setup that runs on a laptop and can be deployed to Vercel + Render/Railway + Supabase.
- NeuroGuard v2 scaffolding for voice enrolment, privacy audit hashes, ZK-FL circuits, Flower-style FL simulation, and Polygon Amoy contracts.
- Option B training path: SenseVoiceSmall as an offline teacher, NeuroGuard as the personalized deployed student model.

## Architecture

```text
Student / Counsellor Browser
          |
          v
Next.js Frontend  <------ Supabase Auth + Realtime
          |
          v
FastAPI Backend
          |
          +--> Random Forest survey model
          +--> Temporal LSTM model
          +--> Gradient Boosting fusion model
          |
          v
Supabase PostgreSQL
```

## Repository Structure

```text
.
+-- backend/
|   +-- app/
|   |   +-- core/              # config and Supabase JWT auth
|   |   +-- services/          # ML, audio features, Supabase repository
|   |   +-- main.py            # FastAPI endpoints
|   |   +-- schemas.py
|   +-- models/                # deployment model placeholder
|   +-- Dockerfile
|   +-- requirements.txt
+-- frontend/
|   +-- src/app/               # Next.js App Router pages
|   +-- src/components/        # dashboard, charts, forms
|   +-- src/lib/               # API, Supabase client, survey schema
+-- PDS MODEL 2/               # Colab plots and trained models
+-- supabase/
|   +-- schema.sql             # tables, indexes, RLS, realtime publication
+-- contracts/                 # Polygon Amoy ConsentDAO and Audit contracts
+-- circuits/                  # Circom local-training and aggregation proof scaffolds
+-- data_factory/              # Hinglish synthetic prompt manifest tooling
+-- docs/
+-- fl/
+-- training/                  # Option B distillation training pipeline
```

## Machine Learning

| Model | File | Purpose |
| --- | --- | --- |
| Random Forest | `neuroguard_rf.pkl` | Predicts stress from 20 survey answers plus engineered features |
| Temporal LSTM | `neuroguard_lstm.keras` | Demonstrates 8-step longitudinal tabular prediction |
| Fusion GB | `neuroguard_fusion.pkl` | Combines tabular and audio probability vectors |
| Tabular scaler | `neuroguard_scaler.pkl` | Scales survey feature matrix |
| Audio scaler | `neuroguard_audio_scaler.pkl` | Present in `PDS MODEL 2`, but no compatible audio Keras model is included |

The backend automatically looks for models in `PDS MODEL 2/` during local development, with `PDS MODEL1/` kept as a fallback for older copies. For Docker or cloud deployment, copy the same model files into `backend/models/`.

Note: if a folder does not include `neuroguard_audio.keras`, the v2 backend can still run the deterministic audio heuristic fallback. A trained audio model should replace that fallback for final evaluation.

## Features

### Student

- Create a new account with email/password.
- Sign in after account creation.
- Fill the 20-question survey.
- Use the survey model and see both Random Forest and temporal LSTM predictions.
- Audio recording works with the trained audio model when present, or the v2 heuristic fallback during development.
- View latest risk class, confidence, probabilities, and trend chart.

### Counsellor

- View assigned students.
- Search and filter student cards.
- Open student history.
- Receive realtime alerts when a new High-Risk prediction is saved.

### Backend

- `GET /health`
- `POST /predict/tabular`
- `POST /predict/audio`
- `POST /predict/full`
- `POST /predict/temporal`
- `GET /students`
- `POST /students/me`
- `GET /students/{id}/history`
- `POST /surveys`
- `POST /audio/upload`
- `POST /enrolments/voice`
- `POST /consent`

## NeuroGuard v2 Additions

- Voice enrolment creates a compact `z_vector` from 1-3 uploaded audio samples.
- Audio prediction now falls back to a deterministic acoustic heuristic if `neuroguard_audio.keras` is unavailable.
- `/predict/stress_voice` combines the external GitHub stress-backbone adapter with the NeuroGuard personalized audio student.
- High-risk predictions write audit hashes to Supabase `audit_events`.
- `contracts/` contains deployable Polygon Amoy `ConsentDAO` and `Audit` contracts.
- `circuits/` contains compact Circom proof scaffolds for local training and FedAvg aggregation.
- `training/` contains the Option B knowledge-distillation path using SenseVoiceSmall as a frozen offline teacher.

See `docs/NEUROGUARD_V2_EXECUTION.md` for the week-by-week execution checklist.

## Option B Distillation

Option B is the recommended v2 training path:

```text
SenseVoiceSmall teacher -> soft SER labels -> NeuroGuard student + z_vector -> deployed stress score
```

The teacher is used only during training. At runtime, FastAPI serves only the NeuroGuard model, so privacy and personalization stay under this project.

```powershell
pip install -r training/requirements.txt
python -m training.train_distillation --manifest data_factory/manifest.csv
```

## External Voice Backbone

The repo has been cloned locally at:

```text
third_party/Stress-Detection-Through-Speech-Emotion-Recognition
```

The upstream repository is MIT licensed, but its trained model/modelconfig assets are not included upstream. NeuroGuard's `POST /predict/stress_voice` route now targets `backbone_independent/` and will use those assets when they are supplied; until then it reports `baseline_available=false` and uses a feature fallback for `stress_baseline`.

See `docs/WINDOWS_REALTIME_SER_PRD.md` for the Windows real-time microphone requirements and artifact checklist.

## Supabase Setup

1. Create a Supabase project.
2. Run `supabase/schema.sql` in the Supabase SQL editor.
3. Enable email/password authentication.
4. Add frontend and backend environment values.
5. For counsellors, create users in Supabase Auth and set user metadata:

```json
{
  "role": "counsellor"
}
```

6. Assign students to counsellors by setting `students.counsellor_id` to the counsellor auth user id.

New student accounts can be created from the app. The backend creates a matching `students` row through `POST /students/me`, so later survey submissions have a valid `student_id`.

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
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
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "models_loaded": true,
  "available_models": {
    "tabular_rf": true,
    "fusion_gb": true,
    "audio_mlp": false,
    "audio_scaler": true,
    "temporal_lstm": true
  }
}
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
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Open:

```text
http://localhost:3000
```

## Sign-Up and Sign-In Behavior

The app supports three clearly separated auth options on the first screen:

| Option | Who uses it | Result |
| --- | --- | --- |
| Student Sign in | Existing student accounts | Opens the student dashboard |
| Student Sign up | New student accounts | Creates a student profile and opens the student dashboard |
| Counsellor Sign in | Counsellor accounts with `role=counsellor` metadata | Opens the counsellor dashboard |

- If Supabase email confirmation is disabled, a new student can sign up and is sent directly to the student dashboard.
- If Supabase email confirmation is enabled, the app shows a confirmation message. After confirming the email, the same user can sign in normally.
- On sign-up or first sign-in, the backend ensures a matching student profile exists, preventing survey-save errors for new users.
- Counsellor Sign in rejects normal student accounts, keeping the counsellor dashboard separate from the student dashboard.

## Deployment Notes

### Frontend

Deploy `frontend/` to Vercel and set:

```text
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_API_BASE_URL
```

### Backend

Deploy `backend/` to Render, Railway, or any Docker host. Copy model files into `backend/models/` before deployment and set:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_AUDIENCE
API_CORS_ORIGINS
MODEL_DIR=/app/models
```

## Validation

Completed local checks:

- Frontend production build passes with Next.js.
- FastAPI starts and loads the model artifacts.
- `/health` returns `models_loaded: true`.
- `/predict/tabular` returns a real Random Forest prediction.
- `/predict/temporal` returns a real LSTM prediction when `neuroguard_lstm.keras` is present.
- Login page renders in the in-app browser without a Next.js error overlay.

## References

- de Filippis, R., & Al Foysal, A. (2024). Comprehensive analysis of stress factors affecting students: a machine learning approach. Discover Artificial Intelligence, 4, 18.
- The RAVDESS dataset.
- Lundberg, S., & Lee, S. (2017). A unified approach to interpreting model predictions. NIPS.
- Chawla, N., et al. (2002). SMOTE. JAIR.
- Supabase documentation.
- FastAPI documentation.

## Team

Course: Python for Data Science

Institution: Sardar Patel Institute of Technology, Mumbai

Project: NeuroGuard, a trimodal early-warning system for student mental health risk
