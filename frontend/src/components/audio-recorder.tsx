"use client";

import { useRef, useState } from "react";
import { Mic, Square, Upload } from "lucide-react";
import { api, getStudentId, type PredictionResponse } from "@/lib/api";
import { ProbabilityChart } from "@/components/probability-chart";
import { RiskBadge } from "@/components/risk-badge";

export function AudioRecorder() {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const [recording, setRecording] = useState(false);
  const [clip, setClip] = useState<Blob | null>(null);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function startRecording() {
    setError("");
    setResult(null);
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    chunksRef.current = [];
    const recorder = new MediaRecorder(stream);
    recorderRef.current = recorder;
    recorder.ondataavailable = (event) => chunksRef.current.push(event.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      setClip(new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" }));
    };
    recorder.start();
    setRecording(true);
    window.setTimeout(() => {
      if (recorder.state === "recording") stopRecording();
    }, 10000);
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setRecording(false);
  }

  async function uploadClip() {
    if (!clip) return;
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("audio", clip, "voice-sample.webm");
      const studentId = await getStudentId();
      if (studentId) formData.append("student_id", studentId);
      formData.append("save", String(Boolean(studentId)));
      const response = await api.post<PredictionResponse>("/predict/audio", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setResult(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audio prediction failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Audio Recorder</h1>
        <p className="text-sm text-[#58706a]">Record a 10-second voice clip and send it to the audio MLP.</p>
      </div>
      {error && <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="rounded-lg border border-[#dce7e2] bg-white p-5">
          <div className="flex flex-wrap gap-3">
            {!recording ? (
              <button
                onClick={startRecording}
                className="focus-ring inline-flex items-center gap-2 rounded-md bg-[#0f766e] px-4 py-2 font-semibold text-white"
              >
                <Mic size={18} />
                Record
              </button>
            ) : (
              <button
                onClick={stopRecording}
                className="focus-ring inline-flex items-center gap-2 rounded-md bg-[#d95d39] px-4 py-2 font-semibold text-white"
              >
                <Square size={18} />
                Stop
              </button>
            )}
            <button
              onClick={uploadClip}
              disabled={!clip || loading}
              className="focus-ring inline-flex items-center gap-2 rounded-md border border-[#dce7e2] bg-white px-4 py-2 font-semibold disabled:opacity-50"
            >
              <Upload size={18} />
              {loading ? "Uploading" : "Upload clip"}
            </button>
          </div>
          <div className="mt-6 rounded-md bg-[#eef5f2] p-4 text-sm text-[#58706a]">
            {recording ? "Recording in progress. It will stop automatically after 10 seconds." : clip ? "Clip captured and ready to upload." : "No clip recorded yet."}
          </div>
          {clip && <audio className="mt-5 w-full" controls src={URL.createObjectURL(clip)} />}
        </div>
        <aside className="rounded-lg border border-[#dce7e2] bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[#58706a]">Audio result</h2>
          {result ? (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <RiskBadge level={result.prediction} />
                <span className="font-mono text-sm text-[#58706a]">{Math.round(result.confidence * 100)}%</span>
              </div>
              <ProbabilityChart values={[result.confidence_0, result.confidence_1, result.confidence_2]} />
            </div>
          ) : (
            <p className="text-sm text-[#58706a]">The MLP prediction will appear here.</p>
          )}
        </aside>
      </div>
    </section>
  );
}
