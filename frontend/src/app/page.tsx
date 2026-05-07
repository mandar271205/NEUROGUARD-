"use client";

import { useState } from "react";
import { Activity, ArrowRight, BrainCircuit, HeartPulse, LockKeyhole, LogIn, ShieldCheck, UserPlus } from "lucide-react";
import { api } from "@/lib/api";
import { hasSupabaseConfig } from "@/lib/config";
import { getSupabase } from "@/lib/supabase";

type AuthMode = "student-signin" | "student-signup" | "counsellor-signin";

export default function LoginPage() {
  const [mode, setMode] = useState<AuthMode>("student-signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function ensureStudentProfile(displayName?: string) {
    const fallbackName = displayName?.trim() || email.split("@")[0] || "Student";
    await api.post("/students/me", { name: fallbackName });
  }

  function routeAfterAuth(role?: string) {
    window.location.href = role === "counsellor" ? "/dashboard/counsellor" : "/dashboard/student";
  }

  function selectMode(nextMode: AuthMode) {
    setMode(nextMode);
    setError("");
    setMessage("");
  }

  async function handleAuth(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const supabase = getSupabase();
    if (!supabase) {
      setError("Supabase keys are missing. Add frontend/.env.local first.");
      return;
    }
    setLoading(true);
    try {
      if (mode === "student-signup") {
        const { data, error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: name.trim(),
              role: "student"
            }
          }
        });
        if (signUpError) throw signUpError;
        if (!data.session && data.user) {
          // Auto-confirm the user since email confirmation is turned off in UI
          try {
            await fetch("/api/auth/auto-confirm", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ userId: data.user.id }),
            });
          } catch (e) {
            console.error("Auto-confirm failed:", e);
          }
          
          setMessage("Account created successfully! You can now sign in.");
          setMode("student-signin");
          return;
        }
        await ensureStudentProfile(name);
        routeAfterAuth("student");
        return;
      }

      const { data, error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password
      });
      if (signInError) throw signInError;
      const role = data.user?.user_metadata?.role;
      if (mode === "counsellor-signin") {
        if (role !== "counsellor") {
          await supabase.auth.signOut();
          setError("This account is not marked as a counsellor. Use Student Sign in or ask the admin to set role=counsellor.");
          return;
        }
        routeAfterAuth("counsellor");
        return;
      }
      if (role === "counsellor") {
        await supabase.auth.signOut();
        setError("This is a counsellor account. Use the Counsellor Sign in option.");
        return;
      }
      if (role !== "counsellor") {
        await ensureStudentProfile(data.user?.user_metadata?.full_name);
      }
      routeAfterAuth(role);
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-8">
      <section className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-7xl items-center gap-8 lg:grid-cols-[1fr_440px]">
        <div className="hidden lg:block">
          <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#dce7e2] bg-white px-3 py-1 text-xs font-semibold text-[#58706a] shadow-sm">
            <span className="size-2 rounded-full bg-[#0f766e]" />
            NeuroGuard v2 live prototype
          </span>
          <span className="mb-5 grid size-14 place-items-center rounded-lg bg-[#0f766e] text-white shadow-xl shadow-teal-900/15">
            <Activity size={24} />
          </span>
          <h1 className="max-w-2xl text-6xl font-semibold leading-tight">
            NeuroGuard student stress intelligence
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-[#58706a]">
            A calmer dashboard for survey ML, voice stress detection, personalized enrolment, adaptive model orchestration, and counsellor alerts.
          </p>
          <div className="mt-8 grid max-w-3xl gap-3 sm:grid-cols-3">
            {[
              { icon: BrainCircuit, title: "Multi-model AI", copy: "RF, LSTM, SER, AAMO" },
              { icon: HeartPulse, title: "Voice pipeline", copy: "Baseline + NeuroGuard" },
              { icon: LockKeyhole, title: "Privacy layer", copy: "Enrolment + audit" }
            ].map((item) => (
              <div key={item.title} className="quiet-card p-4">
                <item.icon size={20} className="text-[#0f766e]" />
                <span className="mt-3 block text-sm font-semibold text-[#17211f]">{item.title}</span>
                <p className="mt-1 text-xs text-[#58706a]">{item.copy}</p>
              </div>
            ))}
          </div>
          <div className="mt-8 flex items-center gap-3 text-sm text-[#58706a]">
            <span className="h-px w-12 bg-[#dce7e2]" />
            Built for student check-ins, counsellor review, and research demos.
          </div>
        </div>
        <div className="surface-card p-6">
          <div className="mb-6 flex items-center gap-3 lg:hidden">
            <span className="grid size-12 place-items-center rounded-lg bg-[#0f766e] text-white">
              <Activity size={24} />
            </span>
            <div>
              <h1 className="text-2xl font-semibold">NeuroGuard</h1>
              <p className="text-sm text-[#58706a]">Student and counsellor access</p>
            </div>
          </div>
          <div className="mb-5 grid grid-cols-3 rounded-lg bg-[#eef5f2] p-1">
            <button
              type="button"
              onClick={() => selectMode("student-signin")}
              className={`focus-ring rounded-md px-3 py-2 text-sm font-semibold ${
                mode === "student-signin" ? "bg-white text-[#17211f] shadow-sm" : "text-[#58706a]"
              }`}
            >
              Student
            </button>
            <button
              type="button"
              onClick={() => selectMode("student-signup")}
              className={`focus-ring rounded-md px-3 py-2 text-sm font-semibold ${
                mode === "student-signup" ? "bg-white text-[#17211f] shadow-sm" : "text-[#58706a]"
              }`}
            >
              New student
            </button>
            <button
              type="button"
              onClick={() => selectMode("counsellor-signin")}
              className={`focus-ring rounded-md px-3 py-2 text-sm font-semibold ${
                mode === "counsellor-signin" ? "bg-white text-[#17211f] shadow-sm" : "text-[#58706a]"
              }`}
            >
              Counsellor
            </button>
          </div>
          <div className="mb-5 rounded-md border border-[#dce7e2] bg-[#f7faf9] px-3 py-2 text-sm text-[#58706a]">
            {mode === "student-signin" && "Student Sign in opens the student dashboard, survey form, and audio recorder."}
            {mode === "student-signup" && "Student Sign up creates a new student account and profile."}
            {mode === "counsellor-signin" && "Counsellor Sign in opens the counsellor dashboard and assigned-student alerts."}
          </div>
        {!hasSupabaseConfig() && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Configure Supabase in <span className="font-mono">frontend/.env.local</span> to enable login.
          </div>
        )}
        <form onSubmit={handleAuth} className="space-y-4">
          {mode === "student-signup" && (
            <label className="block">
              <span className="text-sm font-medium">Full name</span>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                type="text"
                required
                className="focus-ring input-field mt-1 w-full"
              />
            </label>
          )}
          <label className="block">
            <span className="text-sm font-medium">Email</span>
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              required
              className="focus-ring input-field mt-1 w-full"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium">Password</span>
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              required
              minLength={6}
              className="focus-ring input-field mt-1 w-full"
            />
          </label>
          {error && <p className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
          {message && <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{message}</p>}
          <button
            type="submit"
            disabled={loading}
            className="focus-ring btn-primary w-full px-4 py-2.5 disabled:opacity-60"
          >
            {mode === "student-signup" && <UserPlus size={18} />}
            {mode === "student-signin" && <LogIn size={18} />}
            {mode === "counsellor-signin" && <ShieldCheck size={18} />}
            {loading
              ? "Please wait"
              : mode === "student-signup"
                ? "Create student account"
                : mode === "counsellor-signin"
                  ? "Counsellor Sign in"
                  : "Student Sign in"}
            {!loading && <ArrowRight size={17} />}
          </button>
        </form>
        </div>
      </section>
    </main>
  );
}
