"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ClipboardList, Mic, RefreshCw } from "lucide-react";
import { api, getStudentId, type HistoryResponse } from "@/lib/api";
import { ProbabilityChart, RiskTrendChart } from "@/components/probability-chart";
import { RiskBadge } from "@/components/risk-badge";

function latestPrediction(history: HistoryResponse | null) {
  return history?.predictions?.[0] as
    | {
        prediction_class?: number;
        confidence?: number;
        confidence_0?: number;
        confidence_1?: number;
        confidence_2?: number;
        probabilities?: Record<string, number>;
        created_at?: string;
      }
    | undefined;
}

export function StudentDashboard() {
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const studentId = await getStudentId();
      if (!studentId) throw new Error("No student id found in the active Supabase session.");
      const response = await api.get<HistoryResponse>(`/students/${studentId}/history`);
      setHistory(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const latest = latestPrediction(history);
  const probabilityValues: [number, number, number] = [
    Number(latest?.probabilities?.confidence_0 ?? latest?.confidence_0 ?? 0),
    Number(latest?.probabilities?.confidence_1 ?? latest?.confidence_1 ?? 0),
    Number(latest?.probabilities?.confidence_2 ?? latest?.confidence_2 ?? 0)
  ];
  const trend = useMemo(
    () =>
      [...(history?.predictions || [])]
        .reverse()
        .map((item) => ({
          date: new Date(String(item.created_at)).toLocaleDateString(),
          value: Number(item.prediction_class)
        })),
    [history]
  );

  return (
    <section className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-semibold">Student Dashboard</h1>
          <p className="text-sm text-[#58706a]">Latest survey, audio, and risk signals.</p>
        </div>
        <button
          onClick={load}
          className="focus-ring inline-flex items-center gap-2 rounded-md border border-[#dce7e2] bg-white px-3 py-2 text-sm font-medium"
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>
      {error && <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="rounded-lg border border-[#dce7e2] bg-white p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm text-[#58706a]">Current classification</p>
              <div className="mt-2 flex items-center gap-3">
                <RiskBadge level={latest?.prediction_class} />
                <span className="font-mono text-sm text-[#58706a]">
                  {latest ? `${Math.round(Number(latest.confidence || 0) * 100)}% confidence` : "Waiting for first result"}
                </span>
              </div>
            </div>
            <span className="rounded-md bg-[#eef5f2] px-3 py-2 text-xs text-[#58706a]">
              {latest?.created_at ? new Date(latest.created_at).toLocaleString() : "No survey yet"}
            </span>
          </div>
          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            <Link href="/survey" className="focus-ring inline-flex items-center justify-center gap-2 rounded-md bg-[#0f766e] px-4 py-3 font-semibold text-white">
              <ClipboardList size={18} />
              Take Survey
            </Link>
            <Link href="/audio" className="focus-ring inline-flex items-center justify-center gap-2 rounded-md border border-[#dce7e2] bg-white px-4 py-3 font-semibold">
              <Mic size={18} />
              Record Audio
            </Link>
          </div>
          <div className="mt-8">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#58706a]">Risk trend</h2>
            {trend.length ? <RiskTrendChart points={trend} /> : <p className="text-sm text-[#58706a]">No prediction history is available yet.</p>}
          </div>
        </div>
        <div className="flex flex-col gap-4">
          <div className="rounded-lg border border-[#dce7e2] bg-white p-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#58706a]">Probability split</h2>
            {loading ? (
              <p className="text-sm text-[#58706a]">Loading dashboard...</p>
            ) : latest ? (
              <ProbabilityChart values={probabilityValues} />
            ) : (
              <p className="text-sm text-[#58706a]">Submit a survey to generate probabilities.</p>
            )}
          </div>
          {latest && history?.surveys?.[0] && (
            <div className="rounded-lg border border-[#dce7e2] bg-white p-5">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#58706a]">AI Justification</h2>
              <p className="text-sm leading-relaxed text-[#58706a]">
                {generateJustification(Number(latest.prediction_class), history.surveys[0].responses as Record<string, number>)}
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function generateJustification(predictionClass: number, survey: Record<string, number> | undefined): string {
  if (!survey) return "No survey data available to generate a justification.";
  
  const highRiskFactors = [];
  const positiveFactors = [];
  
  if (Number(survey.anxiety_level) >= 6) highRiskFactors.push("high anxiety");
  if (Number(survey.depression) >= 6) highRiskFactors.push("elevated depression indicators");
  if (Number(survey.sleep_quality) <= 4) highRiskFactors.push("poor sleep quality");
  if (Number(survey.academic_performance) <= 4) highRiskFactors.push("academic struggles");
  if (Number(survey.study_load) >= 7) highRiskFactors.push("heavy study load");
  if (Number(survey.peer_pressure) >= 7) highRiskFactors.push("significant peer pressure");
  if (Number(survey.bullying) >= 5) highRiskFactors.push("bullying");
  
  if (Number(survey.self_esteem) >= 7) positiveFactors.push("strong self-esteem");
  if (Number(survey.social_support) >= 7) positiveFactors.push("good social support");
  if (Number(survey.safety) >= 7) positiveFactors.push("a feeling of safety");
  
  if (predictionClass === 0) {
    if (positiveFactors.length > 0) {
      return `The model classified this as Normal primarily because of positive indicators like ${positiveFactors.join(", ")}, and a lack of severe stress factors.`;
    }
    return "The model classified this as Normal because stress indicators (like anxiety, depression, or study load) are within manageable ranges.";
  } else {
    if (highRiskFactors.length > 0) {
      return `The model flagged a Risk primarily due to: ${highRiskFactors.join(", ")}. These factors significantly elevate stress levels and warrant attention.`;
    }
    return "The model flagged a Risk based on a combination of elevated stress signals across the survey.";
  }
}
