"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Fingerprint, Upload } from "lucide-react";
import { api, getStudentId } from "@/lib/api";

type EnrolmentResult = {
  id?: string | null;
  sample_count: number;
  z_vector: number[];
  audio_hashes: string[];
};

export function VoiceEnrolment() {
  const [files, setFiles] = useState<FileList | null>(null);
  const [result, setResult] = useState<EnrolmentResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submitEnrolment() {
    setError("");
    setResult(null);
    if (!files || files.length === 0) {
      setError("Select at least one WAV recording.");
      return;
    }
    setLoading(true);
    try {
      const studentId = await getStudentId();
      if (!studentId) throw new Error("No student id found in the active Supabase session.");
      const formData = new FormData();
      formData.append("student_id", studentId);
      Array.from(files).forEach((file) => formData.append("samples", file, file.name));
      const response = await api.post<EnrolmentResult>("/enrolments/voice", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setResult(response.data);
    } catch (err) {
      if (typeof err === "object" && err && "response" in err) {
        const response = (err as { response?: { data?: { detail?: string } } }).response;
        setError(response?.data?.detail || "Voice enrolment failed.");
      } else {
        setError(err instanceof Error ? err.message : "Voice enrolment failed.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-wrap max-w-6xl">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <p className="section-kicker">Personalization</p>
          <h1 className="mt-1 text-3xl font-semibold">Voice Enrolment</h1>
          <p className="mt-1 text-sm text-[#58706a]">Upload 2-3 short voice clips to create a private personalization vector.</p>
        </div>
        <Link href="/dashboard/student" className="focus-ring btn-secondary px-3 py-2 text-sm">
          <ArrowLeft size={16} />
          Dashboard
        </Link>
      </div>
      {error && <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="surface-card p-5">
          <label className="block">
            <span className="text-sm font-medium">Voice samples</span>
            <input
              type="file"
              accept="audio/*,.wav"
              multiple
              onChange={(event) => setFiles(event.target.files)}
              className="focus-ring input-field mt-2 w-full"
            />
          </label>
          <div className="mt-5 rounded-md bg-[#eef5f2] p-4 text-sm text-[#58706a]">
            {files?.length
              ? `${files.length} sample${files.length === 1 ? "" : "s"} selected.`
              : "Use neutral, natural speech clips of roughly 5-10 seconds each."}
          </div>
          <button
            onClick={submitEnrolment}
            disabled={loading}
            className="focus-ring btn-primary mt-5 px-4 py-2.5 disabled:opacity-60"
          >
            <Upload size={18} />
            {loading ? "Creating vector" : "Create enrolment vector"}
          </button>
        </div>
        <aside className="surface-card p-5">
          <div className="mb-4 flex items-center gap-2">
            <Fingerprint size={18} className="text-[#0f766e]" />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[#58706a]">Personalization</h2>
          </div>
          {result ? (
            <div className="space-y-3 text-sm text-[#58706a]">
              <p>{result.sample_count} samples converted into a {result.z_vector.length}-dimension vector.</p>
              <p className="break-all font-mono text-xs">First hash: {result.audio_hashes[0]}</p>
            </div>
          ) : (
            <p className="text-sm text-[#58706a]">The backend stores hashes and the derived vector, not raw audio blobs.</p>
          )}
        </aside>
      </div>
    </section>
  );
}
