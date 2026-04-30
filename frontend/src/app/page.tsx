"use client";

import { useState } from "react";
import { Activity, LogIn, ShieldCheck, UserPlus } from "lucide-react";
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
        if (!data.session) {
          setMessage("Account created. Confirm your email, then sign in.");
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
    <main className="min-h-screen bg-[#f7faf9] px-4 py-10">
      <section className="mx-auto grid min-h-[calc(100vh-5rem)] w-full max-w-6xl items-center gap-6 lg:grid-cols-[1fr_430px]">
        <div className="hidden lg:block">
          <span className="mb-5 grid size-14 place-items-center rounded-lg bg-[#0f766e] text-white">
            <Activity size={24} />
          </span>
          <h1 className="max-w-xl text-5xl font-semibold leading-tight">
            NeuroGuard
          </h1>
          <p className="mt-4 max-w-xl text-lg text-[#58706a]">
            Separate student and counsellor portals for survey ML, audio biomarkers, history views, and high-risk alerts.
          </p>
          <div className="mt-8 grid max-w-2xl gap-3 sm:grid-cols-3">
            {["Survey RF", "Audio MLP", "Fusion GB"].map((item) => (
              <div key={item} className="rounded-lg border border-[#dce7e2] bg-white p-4 shadow-sm">
                <span className="text-sm font-semibold text-[#0f766e]">{item}</span>
                <p className="mt-2 text-xs text-[#58706a]">Live model pipeline</p>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-[#dce7e2] bg-white p-6 shadow-sm">
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
                className="focus-ring mt-1 w-full rounded-md border border-[#dce7e2] px-3 py-2"
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
              className="focus-ring mt-1 w-full rounded-md border border-[#dce7e2] px-3 py-2"
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
              className="focus-ring mt-1 w-full rounded-md border border-[#dce7e2] px-3 py-2"
            />
          </label>
          {error && <p className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
          {message && <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{message}</p>}
          <button
            type="submit"
            disabled={loading}
            className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#0f766e] px-4 py-2 font-semibold text-white disabled:opacity-60"
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
          </button>
        </form>
        </div>
      </section>
    </main>
  );
}
