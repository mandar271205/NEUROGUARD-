"use client";

import { useMemo, useState } from "react";
import { Send } from "lucide-react";
import { api, getStudentId, type PredictionResponse } from "@/lib/api";
import { surveyQuestions } from "@/lib/survey-schema";
import { ProbabilityChart } from "@/components/probability-chart";
import { RiskBadge } from "@/components/risk-badge";

export function SurveyForm() {
  const [answers, setAnswers] = useState<Record<string, string>>(
    Object.fromEntries(surveyQuestions.map((question) => [question.key, ""]))
  );
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [temporalResult, setTemporalResult] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const complete = useMemo(
    () => surveyQuestions.every((question) => answers[question.key] !== ""),
    [answers]
  );

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    setTemporalResult(null);
    if (!complete) {
      setError("Please answer all questions before submitting.");
      return;
    }
    setLoading(true);
    try {
      const responses = Object.fromEntries(
        Object.entries(answers).map(([key, value]) => [key, Number(value)])
      );
      const studentId = await getStudentId();
      const response = await api.post<PredictionResponse>("/predict/tabular", {
        responses,
        student_id: studentId || undefined,
        save: Boolean(studentId)
      });
      setResult(response.data);
      const temporalResponse = await api.post<PredictionResponse>("/predict/temporal", {
        responses,
        save: false
      });
      setTemporalResult(temporalResponse.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Survey Form</h1>
        <p className="text-sm text-[#58706a]">Answer all 20 fields from the trained StressLevelDataset schema.</p>
      </div>
      {error && <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <form onSubmit={submit} className="rounded-lg border border-[#dce7e2] bg-white p-5">
          <div className="grid gap-4 md:grid-cols-2">
            {surveyQuestions.map((question) => (
              <label key={question.key} className="block rounded-md border border-[#dce7e2] p-3">
                <span className="flex items-center justify-between gap-3 text-sm font-medium">
                  {question.label}
                  <span className="font-mono text-xs text-[#58706a]">{answers[question.key] || "-"}</span>
                </span>
                <input
                  suppressHydrationWarning
                  type="range"
                  min={question.min}
                  max={question.max}
                  step="1"
                  value={answers[question.key] || question.min}
                  onChange={(event) => setAnswers((current) => ({ ...current, [question.key]: event.target.value }))}
                  className="mt-3 w-full accent-[#0f766e]"
                />
                <input
                  suppressHydrationWarning
                  type="number"
                  min={question.min}
                  max={question.max}
                  value={answers[question.key]}
                  onChange={(event) => setAnswers((current) => ({ ...current, [question.key]: event.target.value }))}
                  className="focus-ring mt-2 w-full rounded-md border border-[#dce7e2] px-3 py-2 text-sm"
                />
              </label>
            ))}
          </div>
          <button
            suppressHydrationWarning
            type="submit"
            disabled={loading}
            className="focus-ring mt-5 inline-flex items-center gap-2 rounded-md bg-[#0f766e] px-4 py-2 font-semibold text-white disabled:opacity-60"
          >
            <Send size={18} />
            {loading ? "Predicting" : "Submit survey"}
          </button>
        </form>
        <aside className="rounded-lg border border-[#dce7e2] bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[#58706a]">Results</h2>
          {result ? (
            <div className="space-y-5">
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-sm font-semibold">Random Forest</span>
                  <span className="font-mono text-sm text-[#58706a]">{Math.round(result.confidence * 100)}%</span>
                </div>
                <div className="mb-4">
                  <RiskBadge level={result.prediction} />
                </div>
                <ProbabilityChart values={[result.confidence_0, result.confidence_1, result.confidence_2]} />
              </div>

              <div className="rounded-md border border-[#dce7e2] bg-[#f7faf9] p-3">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[#58706a]">AI Justification</h3>
                <p className="text-sm leading-relaxed text-[#58706a]">
                  {generateJustification(result.prediction, answers)}
                </p>
              </div>

              {temporalResult && (
                <div className="rounded-md border border-[#dce7e2] bg-[#f7faf9] p-3">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-sm font-semibold">Temporal LSTM</span>
                    <span className="font-mono text-sm text-[#58706a]">{Math.round(temporalResult.confidence * 100)}%</span>
                  </div>
                  <RiskBadge level={temporalResult.prediction} />
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-[#58706a]">Random Forest and temporal LSTM results will appear here after submission.</p>
          )}
        </aside>
      </div>
    </section>
  );
}

function generateJustification(predictionClass: number, survey: Record<string, string | number> | undefined): string {
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
