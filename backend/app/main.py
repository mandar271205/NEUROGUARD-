from contextlib import asynccontextmanager
from typing import Annotated
import os
import imageio_ffmpeg

os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware


from app.core.auth import CurrentUser, get_current_user
from app.core.config import get_settings
from app.schemas import (
    FullPredictionResponse,
    HealthResponse,
    PredictionResponse,
    StudentProfileRequest,
    StudentHistory,
    SurveyCreateRequest,
    SurveyPredictionRequest,
)
from app.services.model_service import NeuroGuardModels
from app.services.supabase_service import SupabaseRepository


settings = get_settings()
models = NeuroGuardModels(settings.resolved_model_dir)
repo = SupabaseRepository()


@asynccontextmanager
async def lifespan(_: FastAPI):
    models.load()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _probability_payload(result: dict) -> dict[str, float]:
    return {
        "confidence_0": float(result["confidence_0"]),
        "confidence_1": float(result["confidence_1"]),
        "confidence_2": float(result["confidence_2"]),
    }


def _prediction_response(result: dict, model_type: str, saved_id: str | None = None) -> PredictionResponse:
    return PredictionResponse(
        prediction=int(result["prediction"]),
        confidence_0=float(result["confidence_0"]),
        confidence_1=float(result["confidence_1"]),
        confidence_2=float(result["confidence_2"]),
        confidence=float(result["confidence"]),
        model_type=model_type,
        saved_prediction_id=saved_id,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_dir=str(settings.resolved_model_dir),
        models_loaded=models.loaded,
        available_models=models.available_models(),
    )


@app.post("/predict/tabular", response_model=PredictionResponse)
async def predict_tabular(
    payload: SurveyPredictionRequest,
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> PredictionResponse:
    result = models.predict_tabular(payload.responses)
    saved_id = None
    survey_id = payload.survey_id
    if payload.save and payload.student_id:
        if not survey_id:
            survey = repo.create_survey(payload.student_id, payload.responses)
            survey_id = survey.get("id")
        prediction = repo.create_prediction(
            student_id=payload.student_id,
            survey_id=survey_id,
            model_type="tabular_rf",
            prediction_class=int(result["prediction"]),
            confidence=float(result["confidence"]),
            probabilities=_probability_payload(result),
        )
        saved_id = prediction.get("id")
    return _prediction_response(result, "tabular_rf", saved_id)


@app.post("/predict/audio", response_model=PredictionResponse)
async def predict_audio(
    _: Annotated[CurrentUser, Depends(get_current_user)],
    audio: UploadFile = File(...),
    student_id: str | None = Form(default=None),
    save: bool = Form(default=True),
) -> PredictionResponse:
    try:
        probabilities, features = await models.audio_probabilities_from_upload(audio)
    except Exception as exc:
        print(f"DEBUG EXCEPTION: {type(exc)} - {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Audio error: {str(exc)}",
        ) from exc
    result = models.predict_audio_from_probabilities(probabilities)
    saved_id = None
    audio_id = None
    if save and student_id:
        audio_record = repo.create_audio_file(
            student_id=student_id,
            file_path=audio.filename or "recording",
            extracted_features=[float(value) for value in features.tolist()],
        )
        audio_id = audio_record.get("id")
        prediction = repo.create_prediction(
            student_id=student_id,
            audio_id=audio_id,
            model_type="audio_mlp",
            prediction_class=int(result["prediction"]),
            confidence=float(result["confidence"]),
            probabilities=_probability_payload(result),
        )
        saved_id = prediction.get("id")
    return _prediction_response(result, "audio_mlp", saved_id)


@app.post("/predict/temporal", response_model=PredictionResponse)
async def predict_temporal(
    payload: SurveyPredictionRequest,
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> PredictionResponse:
    result = models.predict_temporal_from_responses(payload.responses)
    return _prediction_response(result, "temporal_lstm")


@app.post("/predict/full", response_model=FullPredictionResponse)
async def predict_full(
    _: Annotated[CurrentUser, Depends(get_current_user)],
    survey_json: str = Form(...),
    audio: UploadFile | None = File(default=None),
    student_id: str | None = Form(default=None),
    save: bool = Form(default=True),
) -> FullPredictionResponse:
    import json

    try:
        responses = json.loads(survey_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="survey_json must be valid JSON.") from exc

    tabular_probs = models.tabular_probabilities(responses)
    audio_source = "synthetic"
    audio_id = None
    features = None
    if audio is not None:
        try:
            audio_probs, features = await models.audio_probabilities_from_upload(audio)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Audio could not be decoded. Please record again or upload a WAV file.",
            ) from exc
        audio_source = "upload"
    else:
        audio_probs = models.synthetic_audio_probabilities()

    result = models.predict_full(tabular_probs, audio_probs)
    saved_id = None
    survey_id = None
    if save and student_id:
        survey = repo.create_survey(student_id, responses)
        survey_id = survey.get("id")
        if features is not None:
            audio_record = repo.create_audio_file(
                student_id=student_id,
                file_path=audio.filename if audio else "synthetic-audio",
                extracted_features=[float(value) for value in features.tolist()],
            )
            audio_id = audio_record.get("id")
        prediction = repo.create_prediction(
            student_id=student_id,
            survey_id=survey_id,
            audio_id=audio_id,
            model_type="fusion_gb",
            prediction_class=int(result["prediction"]),
            confidence=float(result["confidence"]),
            probabilities=_probability_payload(result),
        )
        saved_id = prediction.get("id")

    return FullPredictionResponse(
        prediction=int(result["prediction"]),
        confidence_0=float(result["confidence_0"]),
        confidence_1=float(result["confidence_1"]),
        confidence_2=float(result["confidence_2"]),
        confidence=float(result["confidence"]),
        model_type="fusion_gb",
        saved_prediction_id=saved_id,
        tabular_probabilities=[float(value) for value in tabular_probs.tolist()],
        audio_probabilities=[float(value) for value in audio_probs.tolist()],
        audio_source=audio_source,
    )


@app.get("/students")
async def students(user: Annotated[CurrentUser, Depends(get_current_user)]):
    return repo.list_students_for_counsellor(user.id)


@app.post("/students/me")
async def ensure_student_profile(
    payload: StudentProfileRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    return repo.ensure_student_profile(
        student_id=user.id,
        email=user.email,
        name=payload.name.strip() or user.email or "Student",
    )


@app.get("/students/{student_id}/history", response_model=StudentHistory)
async def student_history(
    student_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> StudentHistory:
    claims = user.claims or {}
    metadata = claims.get("user_metadata") or claims.get("app_metadata") or {}
    claimed_student_id = metadata.get("student_id") if isinstance(metadata, dict) else None
    counsellor_id = None if student_id in {user.id, claimed_student_id} else user.id
    return StudentHistory(**repo.student_history(student_id, counsellor_id))


@app.post("/surveys")
async def create_survey(
    payload: SurveyCreateRequest,
    _: Annotated[CurrentUser, Depends(get_current_user)],
):
    return repo.create_survey(payload.student_id, payload.responses)


@app.post("/audio/upload")
async def upload_audio(
    _: Annotated[CurrentUser, Depends(get_current_user)],
    audio: UploadFile = File(...),
    student_id: str = Form(...),
):
    try:
        probabilities, features = await models.audio_probabilities_from_upload(audio)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Audio could not be decoded. Please record again or upload a WAV file.",
        ) from exc
    audio_record = repo.create_audio_file(
        student_id=student_id,
        file_path=audio.filename or "recording",
        extracted_features=[float(value) for value in features.tolist()],
    )
    return {
        "audio": audio_record,
        "probabilities": [float(value) for value in np.asarray(probabilities).tolist()],
    }
