# NeuroGuard

NeuroGuard is a trimodal early-warning system for student mental health risk. This repo contains:

- `backend/` - FastAPI model-serving API
- `frontend/` - Next.js dashboard and student portal
- `PDS MODEL1/` - your existing Google Colab model outputs
- `supabase/schema.sql` - PostgreSQL tables, indexes, and RLS policies

## Model Files

The backend is already configured to load models from the existing local folder:

```text
PDS MODEL1/
  neuroguard_rf.pkl
  neuroguard_fusion.pkl
  neuroguard_scaler.pkl
  neuroguard_audio.keras
  neuroguard_audio_scaler.pkl
  neuroguard_features.json
```

For deployment, copy those same files into `backend/models/`. The Dockerfile uses `/app/models`.

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

Set these in `backend/.env`:

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

## Frontend Setup

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Set these in `frontend/.env.local`:

```text
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Open `http://localhost:3000`.

## Supabase Setup

1. Create a Supabase project.
2. Run `supabase/schema.sql` in the SQL editor.
3. Enable email/password auth.
4. Create counsellor users in Supabase Auth.
5. Add rows to `students` with `counsellor_id` equal to the counsellor auth user id.
6. Add `role=counsellor` or `student_id=<student uuid>` to user metadata as needed for routing.

The backend uses the service role key for inserts and protected database reads. The frontend uses the anon key for login and realtime alerts.

## API Endpoints

- `GET /health`
- `POST /predict/tabular`
- `POST /predict/audio`
- `POST /predict/full`
- `GET /students`
- `GET /students/{id}/history`
- `POST /surveys`
- `POST /audio/upload`

The tabular endpoint accepts the 20 survey fields from `frontend/src/lib/survey-schema.ts`. The backend adds `risk_score`, `social_isolation`, and `env_stress` before scaling, matching `PDS MODEL1/neuroguard_features.json`.
