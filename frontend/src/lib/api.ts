"use client";

import axios from "axios";
import { apiBaseUrl } from "@/lib/config";
import { getSupabase } from "@/lib/supabase";

export type PredictionResponse = {
  prediction: number;
  confidence_0: number;
  confidence_1: number;
  confidence_2: number;
  confidence: number;
  model_type: string;
  saved_prediction_id?: string | null;
};

export type HistoryResponse = {
  student: Record<string, unknown> | null;
  surveys: Array<Record<string, unknown>>;
  predictions: Array<Record<string, unknown>>;
  audio_files: Array<Record<string, unknown>>;
};

export const api = axios.create({
  baseURL: apiBaseUrl
});

api.interceptors.request.use(async (config) => {
  const supabase = getSupabase();
  const session = supabase ? (await supabase.auth.getSession()).data.session : null;
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

export async function getStudentId() {
  const supabase = getSupabase();
  const session = supabase ? (await supabase.auth.getSession()).data.session : null;
  const metadata = session?.user.user_metadata as { student_id?: string } | undefined;
  return metadata?.student_id || session?.user.id || "";
}
