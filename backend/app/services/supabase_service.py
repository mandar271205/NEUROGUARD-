from typing import Any, Dict, List

from fastapi import HTTPException, status
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
    ) -> Dict[str, Any]:
        payload = {
            "student_id": student_id,
            "survey_id": survey_id,
            "audio_id": audio_id,
            "model_type": model_type,
            "prediction_class": prediction_class,
            "confidence": confidence,
            "probabilities": probabilities or {},
        }
        result = self.client().table("predictions").insert(payload).execute()
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

    def list_students_for_counsellor(self, counsellor_id: str) -> List[Dict[str, Any]]:
        result = (
            self.client()
            .table("students")
            .select("*, predictions(*)")
            .eq("counsellor_id", counsellor_id)
            .execute()
        )
        return result.data or []

    def student_history(
        self, student_id: str, counsellor_id: str | None = None
    ) -> Dict[str, Any]:
        student_query = self.client().table("students").select("*").eq("id", student_id)
        if counsellor_id:
            student_query = student_query.eq("counsellor_id", counsellor_id)
        student_result = student_query.maybe_single().execute()
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
        return {
            "student": student_result.data,
            "surveys": surveys.data or [],
            "predictions": predictions.data or [],
            "audio_files": audio_files.data or [],
        }
