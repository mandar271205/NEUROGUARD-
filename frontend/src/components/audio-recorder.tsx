"use client";

import { useEffect, useRef, useState } from "react";
import { BrainCircuit, Gauge, GitMerge, Mic, Radio, Square, Upload } from "lucide-react";
import { api, getStudentId, type PredictionResponse } from "@/lib/api";
import { ProbabilityChart } from "@/components/probability-chart";
import { RiskBadge } from "@/components/risk-badge";

function mergeBuffers(buffers: Float32Array[]) {
  const totalLength = buffers.reduce((sum, buffer) => sum + buffer.length, 0);
  const result = new Float32Array(totalLength);
  let offset = 0;
  for (const buffer of buffers) {
    result.set(buffer, offset);
    offset += buffer.length;
  }
  return result;
}

function encodeWav(samples: Float32Array, sampleRate: number) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  function writeString(offset: number, value: string) {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  }

  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let index = 0; index < samples.length; index += 1, offset += 2) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }

  return new Blob([view], { type: "audio/wav" });
}

function toPercent(value?: number | null) {
  return Math.max(0, Math.min(100, Math.round(Number(value || 0) * 100)));
}

export function AudioRecorder() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<AudioWorkletNode | null>(null);
  const monitorGainRef = useRef<GainNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Float32Array[]>([]);
  const sampleRateRef = useRef(44100);
  const stopTimerRef = useRef<number | null>(null);
  const [recording, setRecording] = useState(false);
  const [clip, setClip] = useState<Blob | null>(null);
  const [clipUrl, setClipUrl] = useState("");
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState("");
  const [audioAvailable, setAudioAvailable] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function checkAudioModel() {
      try {
        const response = await api.get<{ available_models?: Record<string, boolean> }>("/health");
        setAudioAvailable(Boolean(
          response.data.available_models?.stress_voice_combined ||
          response.data.available_models?.neuroguard_audio_student ||
          response.data.available_models?.audio_mlp ||
          response.data.available_models?.audio_heuristic
        ));
      } catch {
        setAudioAvailable(false);
      }
    }
    void checkAudioModel();
  }, []);

  useEffect(() => {
    return () => {
      if (clipUrl) URL.revokeObjectURL(clipUrl);
    };
  }, [clipUrl]);

  async function startRecording() {
    if (!audioAvailable) return;
    setError("");
    setResult(null);
    setClip(null);
    setClipUrl("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioContext = new AudioContext();
      await audioContext.audioWorklet.addModule("/audio-recorder-worklet.js");
      const source = audioContext.createMediaStreamSource(stream);
      const processor = new AudioWorkletNode(audioContext, "audio-recorder-processor");
      const monitorGain = audioContext.createGain();
      monitorGain.gain.value = 0;

      chunksRef.current = [];
      sampleRateRef.current = audioContext.sampleRate;
      processor.port.onmessage = (event: MessageEvent<Float32Array>) => {
        chunksRef.current.push(new Float32Array(event.data));
      };

      source.connect(processor);
      processor.connect(monitorGain);
      monitorGain.connect(audioContext.destination);

      streamRef.current = stream;
      audioContextRef.current = audioContext;
      sourceRef.current = source;
      processorRef.current = processor;
      monitorGainRef.current = monitorGain;

      setRecording(true);
      stopTimerRef.current = window.setTimeout(stopRecording, 10000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microphone permission failed.");
    }
  }

  function stopRecording() {
    if (stopTimerRef.current) {
      window.clearTimeout(stopTimerRef.current);
      stopTimerRef.current = null;
    }
    processorRef.current?.disconnect();
    processorRef.current?.port.close();
    monitorGainRef.current?.disconnect();
    sourceRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    void audioContextRef.current?.close();

    processorRef.current = null;
    monitorGainRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;
    audioContextRef.current = null;

    if (chunksRef.current.length) {
      const wav = encodeWav(mergeBuffers(chunksRef.current), sampleRateRef.current);
      setClip(wav);
      setClipUrl(URL.createObjectURL(wav));
    }
    setRecording(false);
  }

  async function uploadClip() {
    if (!clip) return;
    if (!audioAvailable) {
      setError("Audio prediction is unavailable. Check the backend health endpoint.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("audio", clip, "voice-sample.wav");
      const studentId = await getStudentId();
      if (studentId) formData.append("student_id", studentId);
      formData.append("save", String(Boolean(studentId)));
      const response = await api.post<PredictionResponse>("/predict/stress_voice", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setResult(response.data);
    } catch (err) {
      if (typeof err === "object" && err && "response" in err) {
        const response = (err as { response?: { data?: { detail?: string } } }).response;
        setError(response?.data?.detail || "Audio prediction failed.");
      } else {
        setError(err instanceof Error ? err.message : "Audio prediction failed.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-wrap max-w-6xl">
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="section-kicker">Voice stress pipeline</p>
          <h1 className="mt-1 text-3xl font-semibold">Audio Recorder</h1>
          <p className="mt-1 max-w-2xl text-sm text-[#58706a]">
          {audioAvailable
            ? "Record a 10-second voice clip and analyze it through the external SER backbone, NeuroGuard student model, and AAMO."
            : "Audio prediction is unavailable for the current backend."}
          </p>
        </div>
        <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${
          audioAvailable ? "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200" : "bg-amber-50 text-amber-900 ring-1 ring-amber-200"
        }`}>
          <Radio size={14} />
          {audioAvailable ? "Backend ready" : "Backend unavailable"}
        </span>
      </div>
      {!audioAvailable && (
        <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Start the backend and check <span className="font-mono">/health</span>. The app can use the trained audio model when present or the v2 heuristic fallback.
        </div>
      )}
      {error && <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="surface-card p-5">
          <div className="mb-5 rounded-lg border border-[#dce7e2] bg-[#f7faf9] p-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold">{recording ? "Listening now" : clip ? "Clip ready" : "Ready to record"}</p>
                <p className="mt-1 text-xs text-[#58706a]">
                  {recording ? "Speak naturally for the strongest signal." : "Use a clean, natural 8-10 second sample."}
                </p>
              </div>
              <span className={`size-3 rounded-full ${recording ? "bg-[#d95d39]" : clip ? "bg-[#0f766e]" : "bg-[#dce7e2]"}`} />
            </div>
            <div className="mt-5 flex h-16 items-end gap-1" aria-hidden="true">
              {Array.from({ length: 36 }).map((_, index) => (
                <span
                  key={index}
                  className={`flex-1 rounded-t-sm ${recording ? "bg-[#0f766e]" : "bg-[#dce7e2]"}`}
                  style={{ height: `${recording ? 22 + ((index * 17) % 39) : 16 + ((index * 9) % 22)}px`, opacity: recording ? 0.55 + ((index % 5) * 0.09) : 0.6 }}
                />
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            {!recording ? (
              <button
                onClick={startRecording}
                disabled={!audioAvailable}
                className="focus-ring btn-primary px-4 py-2.5 disabled:opacity-50"
              >
                <Mic size={18} />
                Record
              </button>
            ) : (
              <button
                onClick={stopRecording}
                className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg bg-[#d95d39] px-4 py-2.5 font-semibold text-white"
              >
                <Square size={18} />
                Stop
              </button>
            )}
            <button
              onClick={uploadClip}
              disabled={!clip || loading || !audioAvailable}
              className="focus-ring btn-secondary px-4 py-2.5 disabled:opacity-50"
            >
              <Upload size={18} />
              {loading ? "Analyzing" : "Analyze clip"}
            </button>
          </div>
          <div className="mt-6 rounded-md bg-[#eef5f2] p-4 text-sm text-[#58706a]">
            {recording ? "Recording in progress. It will stop automatically after 10 seconds." : clip ? "Clip captured and ready to upload." : "No clip recorded yet."}
          </div>
          {clipUrl && <audio className="mt-5 w-full" controls src={clipUrl} />}
        </div>
        <aside className="surface-card p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[#58706a]">Audio result</h2>
          {result ? (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <RiskBadge level={result.prediction} />
                <span className="font-mono text-sm text-[#58706a]">{toPercent(result.confidence)}%</span>
              </div>
              <ProbabilityChart values={[result.confidence_0, result.confidence_1, result.confidence_2]} />
              {typeof result.final_stress === "number" && (
                <div className="space-y-3 rounded-md bg-[#eef5f2] p-3 text-sm text-[#58706a]">
                  {[
                    { label: "Final stress", value: result.final_stress, icon: Gauge, color: "#0f766e" },
                    { label: "Baseline SER", value: result.stress_baseline, icon: GitMerge, color: "#245f9d" },
                    { label: "NeuroGuard", value: result.stress_neuroguard, icon: BrainCircuit, color: "#d95d39" }
                  ].map((item) => (
                    <div key={item.label}>
                      <div className="mb-1 flex items-center justify-between gap-3">
                        <span className="inline-flex items-center gap-2">
                          <item.icon size={15} style={{ color: item.color }} />
                          {item.label}
                        </span>
                        <span className="font-mono">{toPercent(item.value)}%</span>
                      </div>
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${toPercent(item.value)}%`, background: item.color }} />
                      </div>
                    </div>
                  ))}
                  <div className="border-t border-[#d4e2dc] pt-3">
                    <div className="flex justify-between">
                      <span>Baseline weight</span>
                      <span className="font-mono">{toPercent(result.weight_baseline)}%</span>
                    </div>
                    <div className="mt-1 flex justify-between">
                      <span>NeuroGuard weight</span>
                      <span className="font-mono">{toPercent(result.weight_neuroguard)}%</span>
                    </div>
                    <div className="mt-1 flex justify-between">
                      <span>AAMO</span>
                      <span className="font-mono">{result.orchestrator_mode || "n/a"}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-[#58706a]">The audio prediction will appear here.</p>
          )}
        </aside>
      </div>
    </section>
  );
}
