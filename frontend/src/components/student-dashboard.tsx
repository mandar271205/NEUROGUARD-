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
      </div>
    </section>
  );
}
