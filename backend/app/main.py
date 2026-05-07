from contextlib import asynccontextmanager
from typing import Annotated
import os
import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile
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
    StressVoicePredictionResponse,
    StudentProfileRequest,
    StudentHistory,
    SurveyCreateRequest,
    SurveyPredictionRequest,
    ConsentRequest,
    VoiceEnrolmentResponse,
)
from app.services.model_service import NeuroGuardModels
from app.services.supabase_service import SupabaseRepository
from app.services.audio_features import extract_audio_features
from app.services.adaptive_orchestrator import AdaptiveWeightingConfig, AdaptiveWeightingEngine
from app.services.stress_voice_service import StressVoicePipeline


settings = get_settings()
models = NeuroGuardModels(settings.resolved_model_dir)
repo = SupabaseRepository()
adaptive_orchestrator = AdaptiveWeightingEngine(
    AdaptiveWeightingConfig(
        window_size=settings.aamo_window_size,
        min_window_for_adaptive=settings.aamo_min_window_for_adaptive,
        cold_start_weight_baseline=settings.aamo_cold_start_weight_baseline,
        cold_start_weight_neuroguard=settings.aamo_cold_start_weight_neuroguard,
        critical_health_threshold=settings.aamo_critical_health_threshold,
        fallback_weight_baseline=settings.aamo_fallback_weight_baseline,
        fallback_weight_neuroguard=settings.aamo_fallback_weight_neuroguard,
        neuroguard_boost_factor=settings.aamo_neuroguard_boost_factor,
        health_variance_weight=settings.aamo_health_variance_weight,
        health_range_weight=settings.aamo_health_range_weight,
        health_mode_penalty_weight=settings.aamo_health_mode_penalty_weight,
        expected_var_baseline=settings.aamo_expected_var_baseline,
        expected_var_neuroguard=settings.aamo_expected_var_neuroguard,
        expected_range=settings.aamo_expected_range,
    )
)
stress_voice = StressVoicePipeline(
    external_repo_dir=Path(settings.external_stress_repo_dir).expanduser().resolve(),
    student_checkpoint_path=Path(settings.audio_student_checkpoint).expanduser().resolve(),
    baseline_weight=settings.stress_baseline_weight,
    orchestrator=adaptive_orchestrator,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    models.load()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
    risk_level = NeuroGuardModels.risk_level_from_prediction(
        int(result["prediction"]),
        float(result["confidence"]),
    )
    return PredictionResponse(
        prediction=int(result["prediction"]),
        confidence_0=float(result["confidence_0"]),
        confidence_1=float(result["confidence_1"]),
        confidence_2=float(result["confidence_2"]),
        confidence=float(result["confidence"]),
        model_type=model_type,
        saved_prediction_id=saved_id,
        risk_level=risk_level,
        audit_hash=result.get("audit_hash"),
    )


def _prediction_audit_hash(student_id: str | None, result: dict, model_type: str) -> str:
    return NeuroGuardModels.audit_hash_for_payload(
        {
            "student_id": student_id or "anonymous",
            "model_type": model_type,
            "prediction": int(result["prediction"]),
            "confidence": round(float(result["confidence"]), 6),
        }
    )


def _maybe_create_audit_event(
    *,
    student_id: str | None,
    prediction_id: str | None,
    result: dict,
    model_type: str,
) -> str:
    audit_hash = _prediction_audit_hash(student_id, result, model_type)
    result["audit_hash"] = audit_hash
    if not student_id or not prediction_id:
        return audit_hash
    risk_level = NeuroGuardModels.risk_level_from_prediction(
        int(result["prediction"]),
        float(result["confidence"]),
    )
    if risk_level == "high":
        repo.create_audit_event(
            student_id=student_id,
            prediction_id=prediction_id,
            event_type="high_risk_prediction",
            stress_score=float(result["confidence"]),
            audit_hash=audit_hash,
            zk_proof_hash=audit_hash,
        )
    return audit_hash


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    available = models.available_models()
    available["stress_voice_combined"] = True
    available["external_stress_backbone"] = bool(stress_voice.status()["external_backbone"]["ready"])
    available["neuroguard_audio_student"] = bool(stress_voice.status()["student_checkpoint"]["exists"])
    return HealthResponse(
        status="ok",
        model_dir=str(settings.resolved_model_dir),
        models_loaded=models.loaded,
        available_models=available,
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
        risk_level = NeuroGuardModels.risk_level_from_prediction(
            int(result["prediction"]),
            float(result["confidence"]),
        )
        audit_hash = _prediction_audit_hash(payload.student_id, result, "tabular_rf")
        prediction = repo.create_prediction(
            student_id=payload.student_id,
            survey_id=survey_id,
            model_type="tabular_rf",
            prediction_class=int(result["prediction"]),
            confidence=float(result["confidence"]),
            probabilities=_probability_payload(result),
            risk_level=risk_level,
            audit_hash=audit_hash,
        )
        saved_id = prediction.get("id")
        _maybe_create_audit_event(
            student_id=payload.student_id,
            prediction_id=saved_id,
            result=result,
            model_type="tabular_rf",
        )
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
        risk_level = NeuroGuardModels.risk_level_from_prediction(
            int(result["prediction"]),
            float(result["confidence"]),
        )
        audit_hash = _prediction_audit_hash(student_id, result, "audio_mlp")
        prediction = repo.create_prediction(
            student_id=student_id,
            audio_id=audio_id,
            model_type="audio_mlp",
            prediction_class=int(result["prediction"]),
            confidence=float(result["confidence"]),
            probabilities=_probability_payload(result),
            risk_level=risk_level,
            audit_hash=audit_hash,
        )
        saved_id = prediction.get("id")
        _maybe_create_audit_event(
            student_id=student_id,
            prediction_id=saved_id,
            result=result,
            model_type="audio_mlp",
        )
    return _prediction_response(result, "audio_mlp", saved_id)


@app.post("/predict/stress_voice", response_model=StressVoicePredictionResponse)
async def predict_stress_voice(
    _: Annotated[CurrentUser, Depends(get_current_user)],
    audio: UploadFile = File(...),
    student_id: str | None = Form(default=None),
    save: bool = Form(default=True),
    gender: str = Form(default="male"),
    baseline_weight: float | None = Form(default=None),
) -> StressVoicePredictionResponse:
    suffix = Path(audio.filename or "voice.wav").suffix or ".wav"
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = Path(tmp.name)

    try:
        z_vector = None
        if student_id:
            try:
                enrolment = repo.latest_voice_enrolment(student_id)
                raw_z = enrolment.get("z_vector") if enrolment else None
                if isinstance(raw_z, list):
                    z_vector = [float(value) for value in raw_z]
            except HTTPException:
                z_vector = None

        voice_result = stress_voice.predict(
            tmp_path,
            z_vector=z_vector,
            gender=gender,
            baseline_weight=baseline_weight,
            student_id=student_id,
        )
        probabilities = voice_result.probabilities
        result = {
            "prediction": voice_result.prediction,
            "confidence_0": float(probabilities[0]),
            "confidence_1": float(probabilities[1]),
            "confidence_2": float(probabilities[2]),
            "confidence": voice_result.confidence,
        }
        saved_id = None
        if save and student_id:
            audio_record = {}
            try:
                features = extract_audio_features(tmp_path)
                audio_record = repo.create_audio_file(
                    student_id=student_id,
                    file_path=audio.filename or "stress-voice-recording",
                    extracted_features=[float(value) for value in features.tolist()],
                )
            except HTTPException:
                audio_record = {}
            risk_level = NeuroGuardModels.risk_level_from_prediction(
                int(result["prediction"]),
                float(result["confidence"]),
            )
            audit_hash = _prediction_audit_hash(student_id, result, "stress_voice_combined")
            try:
                prediction = repo.create_prediction(
                    student_id=student_id,
                    audio_id=audio_record.get("id"),
                    model_type="stress_voice_combined",
                    prediction_class=int(result["prediction"]),
                    confidence=float(result["confidence"]),
                    probabilities={
                        **_probability_payload(result),
                        "stress_baseline": voice_result.baseline.score,
                        "stress_neuroguard": voice_result.student.score,
                        "final_stress": voice_result.final_stress,
                        "weight_baseline": voice_result.orchestration.weight_baseline,
                        "weight_neuroguard": voice_result.orchestration.weight_neuroguard,
                        "health_baseline": voice_result.orchestration.health_baseline.score,
                        "health_neuroguard": voice_result.orchestration.health_neuroguard.score,
                        "orchestrator_mode": voice_result.orchestration.mode,
                        "orchestrator_window_scope": voice_result.orchestration.window_scope,
                        "orchestrator_window_size": voice_result.orchestration.window_size,
                    },
                    risk_level=risk_level,
                    audit_hash=audit_hash,
                )
                saved_id = prediction.get("id")
            except HTTPException:
                saved_id = None
            if saved_id:
                _maybe_create_audit_event(
                    student_id=student_id,
                    prediction_id=saved_id,
                    result=result,
                    model_type="stress_voice_combined",
                )

        return StressVoicePredictionResponse(
            prediction=int(result["prediction"]),
            confidence_0=float(result["confidence_0"]),
            confidence_1=float(result["confidence_1"]),
            confidence_2=float(result["confidence_2"]),
            confidence=float(result["confidence"]),
            model_type="stress_voice_combined",
            saved_prediction_id=saved_id,
            risk_level=NeuroGuardModels.risk_level_from_prediction(
                int(result["prediction"]),
                float(result["confidence"]),
            ),
            audit_hash=result.get("audit_hash"),
            stress_baseline=voice_result.baseline.score,
            stress_neuroguard=voice_result.student.score,
            final_stress=voice_result.final_stress,
            weight_baseline=voice_result.orchestration.weight_baseline,
            weight_neuroguard=voice_result.orchestration.weight_neuroguard,
            health_baseline=voice_result.orchestration.health_baseline.score,
            health_neuroguard=voice_result.orchestration.health_neuroguard.score,
            orchestrator_mode=voice_result.orchestration.mode,
            orchestrator_window_scope=voice_result.orchestration.window_scope,
            orchestrator_window_size=voice_result.orchestration.window_size,
            baseline_source=voice_result.baseline.source,
            neuroguard_source=voice_result.student.source,
            baseline_available=voice_result.baseline.available,
            blend={
                "baseline_weight": voice_result.orchestration.weight_baseline,
                "neuroguard_weight": voice_result.orchestration.weight_neuroguard,
                "health_baseline": voice_result.orchestration.health_baseline.score,
                "health_neuroguard": voice_result.orchestration.health_neuroguard.score,
            },
        )
    finally:
        tmp_path.unlink(missing_ok=True)


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
        risk_level = NeuroGuardModels.risk_level_from_prediction(
            int(result["prediction"]),
            float(result["confidence"]),
        )
        audit_hash = _prediction_audit_hash(student_id, result, "fusion_gb")
        prediction = repo.create_prediction(
            student_id=student_id,
            survey_id=survey_id,
            audio_id=audio_id,
            model_type="fusion_gb",
            prediction_class=int(result["prediction"]),
            confidence=float(result["confidence"]),
            probabilities=_probability_payload(result),
            risk_level=risk_level,
            audit_hash=audit_hash,
        )
        saved_id = prediction.get("id")
        _maybe_create_audit_event(
            student_id=student_id,
            prediction_id=saved_id,
            result=result,
            model_type="fusion_gb",
        )

    return FullPredictionResponse(
        prediction=int(result["prediction"]),
        confidence_0=float(result["confidence_0"]),
        confidence_1=float(result["confidence_1"]),
        confidence_2=float(result["confidence_2"]),
        confidence=float(result["confidence"]),
        model_type="fusion_gb",
        saved_prediction_id=saved_id,
        risk_level=NeuroGuardModels.risk_level_from_prediction(
            int(result["prediction"]),
            float(result["confidence"]),
        ),
        audit_hash=result.get("audit_hash"),
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


@app.post("/enrolments/voice", response_model=VoiceEnrolmentResponse)
async def create_voice_enrolment(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    student_id: str = Form(...),
    samples: list[UploadFile] = File(...),
) -> VoiceEnrolmentResponse:
    if student_id != user.id:
        claims = user.claims or {}
        metadata = claims.get("user_metadata") or claims.get("app_metadata") or {}
        if not isinstance(metadata, dict) or metadata.get("role") != "counsellor":
            raise HTTPException(status_code=403, detail="Cannot enrol voice for another user.")
    features = []
    audio_hashes = []
    for sample in samples:
        suffix = Path(sample.filename or "voice.wav").suffix or ".wav"
        content = await sample.read()
        audio_hashes.append("0x" + hashlib.sha256(content).hexdigest())
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        try:
            from app.services.audio_features import extract_audio_features

            features.append(extract_audio_features(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)
    z_vector = models.enrolment_vector_from_features(features)
    record = repo.create_voice_enrolment(
        student_id=student_id,
        z_vector=z_vector,
        sample_count=len(features),
        audio_hashes=audio_hashes,
    )
    return VoiceEnrolmentResponse(
        id=record.get("id"),
        student_id=student_id,
        sample_count=len(features),
        z_vector=z_vector,
        audio_hashes=audio_hashes,
        created_at=record.get("created_at"),
    )


@app.post("/consent")
async def update_consent(
    payload: ConsentRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    if payload.student_id != user.id:
        raise HTTPException(status_code=403, detail="Students can only update their own consent.")
    return repo.upsert_consent(payload.model_dump())
