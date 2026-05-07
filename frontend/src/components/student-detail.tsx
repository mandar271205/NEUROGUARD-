"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type HistoryResponse } from "@/lib/api";
import { RiskTrendChart } from "@/components/probability-chart";
import { RiskBadge } from "@/components/risk-badge";

export function StudentDetail({ studentId }: { studentId: string }) {
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const response = await api.get<HistoryResponse>(`/students/${studentId}/history`);
        setHistory(response.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load student history.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [studentId]);

  const predictions = useMemo(() => history?.predictions || [], [history?.predictions]);
  const trend = useMemo(
    () =>
      [...predictions].reverse().map((item) => ({
        date: new Date(String(item.created_at)).toLocaleDateString(),
        value: Number(item.prediction_class)
      })),
    [predictions]
  );

  return (
    <section className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">{String(history?.student?.name || "Student Detail")}</h1>
        <p className="text-sm text-[#58706a]">{String(history?.student?.email || studentId)}</p>
      </div>
      {error && <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="rounded-lg border border-[#dce7e2] bg-white p-5">
          <h2 className="mb-4 font-semibold">Risk timeline</h2>
          {loading ? <p className="text-sm text-[#58706a]">Loading history...</p> : trend.length ? <RiskTrendChart points={trend} /> : <p className="text-sm text-[#58706a]">No predictions yet.</p>}
        </div>
        <aside className="rounded-lg border border-[#dce7e2] bg-white p-5">
          <h2 className="mb-4 font-semibold">Prediction history</h2>
          {predictions.length ? (
            <div className="space-y-3">
              {predictions.map((prediction, index) => (
                <div key={String(prediction.id || index)} className="rounded-md border border-[#dce7e2] p-3">
                  <div className="flex items-center justify-between gap-3">
                    <RiskBadge level={Number(prediction.prediction_class)} />
                    <span className="font-mono text-xs text-[#58706a]">
                      {Math.round(Number(prediction.confidence || 0) * 100)}%
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-xs text-[#58706a]">
                    <span>{String(prediction.model_type || "model")}</span>
                    <span>{prediction.created_at ? new Date(String(prediction.created_at)).toLocaleString() : ""}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[#58706a]">No saved predictions.</p>
          )}
        </aside>
      </div>
    </section>
  );
}
