"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Bell, ClipboardList, Home, LogOut, Mic, Users } from "lucide-react";
import { getSupabase } from "@/lib/supabase";

const nav = [
  { href: "/dashboard/student", label: "Student", icon: Home },
  { href: "/survey", label: "Survey", icon: ClipboardList },
  { href: "/audio", label: "Audio", icon: Mic },
  { href: "/dashboard/counsellor", label: "Counsellor", icon: Users }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  async function logout() {
    const supabase = getSupabase();
    if (supabase) await supabase.auth.signOut();
    window.location.href = "/";
  }

  return (
    <main className="min-h-screen text-[#17211f]">
      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r border-white/10 bg-[#14211f] p-5 text-white shadow-2xl lg:block">
        <Link href="/dashboard/student" className="flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-lg bg-[#1f8a7a] shadow-lg shadow-teal-950/25">
            <Activity size={22} />
          </span>
          <span>
            <span className="block text-lg font-semibold">NeuroGuard</span>
            <span className="text-xs text-teal-100">Adaptive stress intelligence</span>
          </span>
        </Link>
        <div className="mt-6 rounded-lg border border-white/10 bg-white/[0.06] p-3">
          <p className="text-xs font-semibold uppercase text-teal-100">Live Stack</p>
          <p className="mt-1 text-sm text-white">Survey ML + Voice SER + AAMO</p>
        </div>
        <nav className="mt-8 space-y-2">
          {nav.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                  active
                    ? "bg-white text-[#14211f] shadow-lg shadow-black/10"
                    : "text-teal-50 hover:bg-white/10"
                }`}
              >
                <item.icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="absolute bottom-5 left-5 right-5 space-y-2">
          <Link
            href="/dashboard/counsellor#alerts"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-teal-50 transition hover:bg-white/10"
          >
            <Bell size={18} />
            Alerts
          </Link>
          <button
            suppressHydrationWarning
            type="button"
            onClick={logout}
            className="focus-ring flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-teal-50 transition hover:bg-white/10"
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </aside>
      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-[#dce7e2] bg-white/95 px-4 py-3 backdrop-blur lg:hidden">
          <div className="flex items-center justify-between">
            <Link href="/dashboard/student" className="flex items-center gap-2 font-semibold">
              <span className="grid size-8 place-items-center rounded-lg bg-[#0f766e] text-white">
                <Activity size={17} />
              </span>
              NeuroGuard
            </Link>
            <span className="rounded-full bg-[#eef5f2] px-3 py-1 text-xs font-semibold text-[#58706a]">
              v2
            </span>
          </div>
          <div className="flex gap-2">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-label={item.label}
                className={`mt-3 rounded-md p-2 ${
                  pathname === item.href ? "bg-[#0f766e] text-white" : "text-[#58706a]"
                }`}
              >
                <item.icon size={18} />
              </Link>
            ))}
          </div>
        </header>
        {children}
      </div>
    </main>
  );
}
