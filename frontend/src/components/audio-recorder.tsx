"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, Square, Upload } from "lucide-react";
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

export function AudioRecorder() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
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
        setAudioAvailable(Boolean(response.data.available_models?.audio_mlp));
      } catch {
        setAudioAvailable(false);
      }
    }
    void checkAudioModel();
  }, []);

  async function startRecording() {
    if (!audioAvailable) return;
    setError("");
    setResult(null);
    setClip(null);
    setClipUrl("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      chunksRef.current = [];
      sampleRateRef.current = audioContext.sampleRate;
      processor.onaudioprocess = (event) => {
        chunksRef.current.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      streamRef.current = stream;
      audioContextRef.current = audioContext;
      sourceRef.current = source;
      processorRef.current = processor;

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
    sourceRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    void audioContextRef.current?.close();

    processorRef.current = null;
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
      setError("Audio prediction is unavailable because the current model folder does not include neuroguard_audio.keras.");
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
      const response = await api.post<PredictionResponse>("/predict/audio", formData, {
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
    <section className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Audio Recorder</h1>
        <p className="text-sm text-[#58706a]">
          {audioAvailable
            ? "Record a 10-second voice clip and send it to the audio MLP."
            : "Audio prediction is unavailable for the current PDS MODEL 2 folder."}
        </p>
      </div>
      {!audioAvailable && (
        <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Add a compatible <span className="font-mono">neuroguard_audio.keras</span> file to enable this page. Survey and temporal LSTM predictions still work.
        </div>
      )}
      {error && <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="rounded-lg border border-[#dce7e2] bg-white p-5">
          <div className="flex flex-wrap gap-3">
            {!recording ? (
              <button
                onClick={startRecording}
                disabled={!audioAvailable}
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
              disabled={!clip || loading || !audioAvailable}
              className="focus-ring inline-flex items-center gap-2 rounded-md border border-[#dce7e2] bg-white px-4 py-2 font-semibold disabled:opacity-50"
            >
              <Upload size={18} />
              {loading ? "Uploading" : "Upload clip"}
            </button>
          </div>
          <div className="mt-6 rounded-md bg-[#eef5f2] p-4 text-sm text-[#58706a]">
            {recording ? "Recording in progress. It will stop automatically after 10 seconds." : clip ? "Clip captured and ready to upload." : "No clip recorded yet."}
          </div>
          {clipUrl && <audio className="mt-5 w-full" controls src={clipUrl} />}
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
