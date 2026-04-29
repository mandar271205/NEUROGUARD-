"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Search, Users } from "lucide-react";
import { api } from "@/lib/api";
import { AlertsPanel } from "@/components/alerts-panel";
import { RiskBadge } from "@/components/risk-badge";

type Prediction = {
  prediction_class?: number;
  confidence?: number;
  created_at?: string;
};

type Student = {
  id: string;
  name?: string;
  email?: string;
  enrollment_year?: number;
  predictions?: Prediction[];
};

function latestPrediction(student: Student) {
  return [...(student.predictions || [])].sort((a, b) =>
    String(b.created_at || "").localeCompare(String(a.created_at || ""))
  )[0];
}

export function CounsellorDashboard() {
  const [students, setStudents] = useState<Student[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const response = await api.get<Student[]>("/students");
        setStudents(response.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load students.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  const filtered = useMemo(
    () =>
      students.filter((student) => {
        const text = `${student.name || ""} ${student.email || ""}`.toLowerCase();
        return text.includes(query.toLowerCase());
      }),
    [query, students]
  );

  return (
    <section className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
        <div>
          <h1 className="text-2xl font-semibold">Counsellor Dashboard</h1>
          <p className="text-sm text-[#58706a]">Assigned students, latest risks, and realtime high-risk alerts.</p>
        </div>
        <label className="relative block w-full max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#58706a]" size={17} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search students"
            className="focus-ring w-full rounded-md border border-[#dce7e2] bg-white py-2 pl-10 pr-3 text-sm"
          />
        </label>
      </div>
      {error && <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
      <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
        <div className="rounded-lg border border-[#dce7e2] bg-white">
          <div className="flex items-center gap-2 border-b border-[#dce7e2] p-4">
            <Users size={18} className="text-[#0f766e]" />
            <h2 className="font-semibold">Students</h2>
          </div>
          {loading ? (
            <p className="p-4 text-sm text-[#58706a]">Loading students...</p>
          ) : filtered.length ? (
            <div className="divide-y divide-[#dce7e2]">
              {filtered.map((student) => {
                const latest = latestPrediction(student);
                return (
                  <Link
                    key={student.id}
                    href={`/dashboard/students/${student.id}`}
                    className="grid gap-3 p-4 hover:bg-[#eef5f2] md:grid-cols-[1fr_140px_120px]"
                  >
                    <span>
                      <span className="block font-medium">{student.name || "Unnamed student"}</span>
                      <span className="text-sm text-[#58706a]">{student.email || student.id}</span>
                    </span>
                    <RiskBadge level={latest?.prediction_class} />
                    <span className="font-mono text-sm text-[#58706a]">
                      {latest?.created_at ? new Date(latest.created_at).toLocaleDateString() : "No history"}
                    </span>
                  </Link>
                );
              })}
            </div>
          ) : (
            <p className="p-4 text-sm text-[#58706a]">No assigned students found.</p>
          )}
        </div>
        <AlertsPanel />
      </div>
    </section>
  );
}
