from typing import Any, Dict, List

from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client, create_client

from app.core.config import get_settings


class SupabaseRepository:
    def __init__(self) -> None:
        self._client: Client | None = None

    def client(self) -> Client:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
            )
        if self._client is None:
            self._client = create_client(
                settings.supabase_url, settings.supabase_service_role_key
            )
        return self._client

    @staticmethod
    def _is_schema_cache_error(exc: Exception) -> bool:
        if not isinstance(exc, APIError):
            return False
        message = str(exc)
        return any(
            marker in message
            for marker in (
                "PGRST204",
                "PGRST205",
                "schema cache",
                "Could not find the",
                "violates check constraint",
            )
        )

    def create_survey(self, student_id: str, responses: Dict[str, float]) -> Dict[str, Any]:
        result = (
            self.client()
            .table("surveys")
            .insert({"student_id": student_id, "responses": responses})
            .execute()
        )
        return result.data[0] if result.data else {}

    def create_prediction(
        self,
        *,
        student_id: str,
        model_type: str,
        prediction_class: int,
        confidence: float,
        survey_id: str | None = None,
        audio_id: str | None = None,
        probabilities: Dict[str, float] | None = None,
        risk_level: str | None = None,
        audit_hash: str | None = None,
    ) -> Dict[str, Any]:
        payload = {
            "student_id": student_id,
            "survey_id": survey_id,
            "audio_id": audio_id,
            "model_type": model_type,
            "prediction_class": prediction_class,
            "confidence": confidence,
            "probabilities": probabilities or {},
            "risk_level": risk_level,
            "audit_hash": audit_hash,
        }
        try:
            result = self.client().table("predictions").insert(payload).execute()
        except Exception as exc:
            if not self._is_schema_cache_error(exc):
                raise
            legacy_payload = {
                key: value
                for key, value in payload.items()
                if key not in {"risk_level", "audit_hash"}
            }
            if model_type == "stress_voice_combined":
                # Older schemas reject this new model type. Keep prediction serving
                # working and let the caller continue without a saved row.
                return {}
            result = self.client().table("predictions").insert(legacy_payload).execute()
        return result.data[0] if result.data else {}

    def create_audio_file(
        self, student_id: str, file_path: str, extracted_features: List[float]
    ) -> Dict[str, Any]:
        result = (
            self.client()
            .table("audio_files")
            .insert(
                {
                    "student_id": student_id,
                    "file_path": file_path,
                    "extracted_features": extracted_features,
                }
            )
            .execute()
        )
        return result.data[0] if result.data else {}

    def create_voice_enrolment(
        self,
        *,
        student_id: str,
        z_vector: List[float],
        sample_count: int,
        audio_hashes: List[str],
    ) -> Dict[str, Any]:
        try:
            result = (
                self.client()
                .table("voice_enrolments")
                .insert(
                    {
                        "student_id": student_id,
                        "z_vector": z_vector,
                        "sample_count": sample_count,
                        "audio_hashes": audio_hashes,
                    }
                )
                .execute()
            )
        except Exception as exc:
            if self._is_schema_cache_error(exc):
                return {
                    "student_id": student_id,
                    "z_vector": z_vector,
                    "sample_count": sample_count,
                    "audio_hashes": audio_hashes,
                }
            raise
        return result.data[0] if result.data else {}

    def latest_voice_enrolment(self, student_id: str) -> Dict[str, Any] | None:
        try:
            result = (
                self.client()
                .table("voice_enrolments")
                .select("*")
                .eq("student_id", student_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            if self._is_schema_cache_error(exc):
                return None
            raise
        return result.data[0] if result.data else None

    def upsert_consent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = (
                self.client()
                .table("consent_logs")
                .insert(payload)
                .execute()
            )
        except Exception as exc:
            if self._is_schema_cache_error(exc):
                return payload
            raise
        return result.data[0] if result.data else payload

    def create_audit_event(
        self,
        *,
        student_id: str,
        prediction_id: str | None,
        event_type: str,
        stress_score: float,
        audit_hash: str,
        zk_proof_hash: str | None = None,
        contract_tx_hash: str | None = None,
    ) -> Dict[str, Any]:
        try:
            result = (
                self.client()
                .table("audit_events")
                .insert(
                    {
                        "student_id": student_id,
                        "prediction_id": prediction_id,
                        "event_type": event_type,
                        "stress_score": stress_score,
                        "audit_hash": audit_hash,
                        "zk_proof_hash": zk_proof_hash,
                        "contract_tx_hash": contract_tx_hash,
                    }
                )
                .execute()
            )
        except Exception as exc:
            if self._is_schema_cache_error(exc):
                return {}
            raise
        return result.data[0] if result.data else {}

    def list_students_for_counsellor(self, counsellor_id: str) -> List[Dict[str, Any]]:
        result = (
            self.client()
            .table("students")
            .select("*, predictions(*)")
            .eq("counsellor_id", counsellor_id)
            .execute()
        )
        return result.data or []

    def ensure_student_profile(
        self, student_id: str, email: str | None, name: str
    ) -> Dict[str, Any]:
        payload = {
            "id": student_id,
            "email": email,
            "name": name,
        }
        result = (
            self.client()
            .table("students")
            .upsert(payload, on_conflict="id")
            .execute()
        )
        return result.data[0] if result.data else payload

    def student_history(
        self, student_id: str, counsellor_id: str | None = None
    ) -> Dict[str, Any]:
        student_query = self.client().table("students").select("*").eq("id", student_id)
        if counsellor_id:
            student_query = student_query.eq("counsellor_id", counsellor_id)
        student_result = student_query.maybe_single().execute()
        student_data = student_result.data if student_result else None
        if counsellor_id and not student_data:
            return {
                "student": None,
                "surveys": [],
                "predictions": [],
                "audio_files": [],
                "voice_enrolments": [],
                "audit_events": [],
            }

        surveys = (
            self.client()
            .table("surveys")
            .select("*")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .execute()
        )
        predictions = (
            self.client()
            .table("predictions")
            .select("*")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .execute()
        )
        audio_files = (
            self.client()
            .table("audio_files")
            .select("*")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .execute()
        )
        try:
            voice_enrolments = (
                self.client()
                .table("voice_enrolments")
                .select("*")
                .eq("student_id", student_id)
                .order("created_at", desc=True)
                .execute()
            )
            voice_enrolment_data = voice_enrolments.data or []
        except Exception as exc:
            if not self._is_schema_cache_error(exc):
                raise
            voice_enrolment_data = []
        try:
            audit_events = (
                self.client()
                .table("audit_events")
                .select("*")
                .eq("student_id", student_id)
                .order("created_at", desc=True)
                .execute()
            )
            audit_event_data = audit_events.data or []
        except Exception as exc:
            if not self._is_schema_cache_error(exc):
                raise
            audit_event_data = []
        return {
            "student": student_data,
            "surveys": surveys.data or [],
            "predictions": predictions.data or [],
            "audio_files": audio_files.data or [],
            "voice_enrolments": voice_enrolment_data,
            "audit_events": audit_event_data,
        }
