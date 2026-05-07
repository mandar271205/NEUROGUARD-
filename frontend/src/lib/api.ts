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
  audit_hash?: string | null;
  risk_level?: string | null;
  stress_baseline?: number;
  stress_neuroguard?: number;
  final_stress?: number;
  weight_baseline?: number;
  weight_neuroguard?: number;
  health_baseline?: number;
  health_neuroguard?: number;
  orchestrator_mode?: string;
  orchestrator_window_scope?: string;
  orchestrator_window_size?: number;
  baseline_source?: string;
  neuroguard_source?: string;
  baseline_available?: boolean;
};

export type HistoryResponse = {
  student: Record<string, unknown> | null;
  surveys: Array<Record<string, unknown>>;
  predictions: Array<Record<string, unknown>>;
  audio_files: Array<Record<string, unknown>>;
  voice_enrolments: Array<Record<string, unknown>>;
  audit_events: Array<Record<string, unknown>>;
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
