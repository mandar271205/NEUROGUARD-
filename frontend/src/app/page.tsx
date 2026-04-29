"use client";

import { useState } from "react";
import { Activity, LogIn } from "lucide-react";
import { hasSupabaseConfig } from "@/lib/config";
import { getSupabase } from "@/lib/supabase";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function login(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const supabase = getSupabase();
    if (!supabase) {
      setError("Supabase keys are missing. Add frontend/.env.local first.");
      return;
    }
    setLoading(true);
    const { data, error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password
    });
    setLoading(false);
    if (signInError) {
      setError(signInError.message);
      return;
    }
    const role = data.user?.user_metadata?.role;
    window.location.href = role === "counsellor" ? "/dashboard/counsellor" : "/dashboard/student";
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#f7faf9] px-4 py-10">
      <section className="w-full max-w-md rounded-lg border border-[#dce7e2] bg-white p-6 shadow-sm">
        <div className="mb-8 flex items-center gap-3">
          <span className="grid size-12 place-items-center rounded-lg bg-[#0f766e] text-white">
            <Activity size={24} />
          </span>
          <div>
            <h1 className="text-2xl font-semibold">NeuroGuard</h1>
            <p className="text-sm text-[#58706a]">Student mental health risk dashboard</p>
          </div>
        </div>
        {!hasSupabaseConfig() && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Configure Supabase in <span className="font-mono">frontend/.env.local</span> to enable login.
          </div>
        )}
        <form onSubmit={login} className="space-y-4">
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
              className="focus-ring mt-1 w-full rounded-md border border-[#dce7e2] px-3 py-2"
            />
          </label>
          {error && <p className="text-sm text-rose-700">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#0f766e] px-4 py-2 font-semibold text-white disabled:opacity-60"
          >
            <LogIn size={18} />
            {loading ? "Signing in" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
