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
    +-- schema.sql             # tables, indexes, RLS, realtime publication
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

Note: `PDS MODEL 2` does not include `neuroguard_audio.keras`. The app therefore disables audio prediction until a compatible audio model file is added. Survey, fusion-with-neutral-audio, and temporal LSTM paths still load.

## Features

### Student

- Create a new account with email/password.
- Sign in after account creation.
- Fill the 20-question survey.
- Use the survey model and see both Random Forest and temporal LSTM predictions.
- Audio recording is shown only as available when the model folder includes `neuroguard_audio.keras`.
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
