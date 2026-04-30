"use client";

import Link from "next/link";
import { Activity, Bell, ClipboardList, Home, LogOut, Mic, Users } from "lucide-react";
import { getSupabase } from "@/lib/supabase";

const nav = [
  { href: "/dashboard/student", label: "Student", icon: Home },
  { href: "/survey", label: "Survey", icon: ClipboardList },
  { href: "/audio", label: "Audio", icon: Mic },
  { href: "/dashboard/counsellor", label: "Counsellor", icon: Users }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  async function logout() {
    const supabase = getSupabase();
    if (supabase) await supabase.auth.signOut();
    window.location.href = "/";
  }

  return (
    <main className="min-h-screen bg-[#f7faf9] text-[#17211f]">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-[#dce7e2] bg-[#14211f] p-5 text-white lg:block">
        <Link href="/dashboard/student" className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-lg bg-[#1f8a7a]">
            <Activity size={22} />
          </span>
          <span>
            <span className="block text-lg font-semibold">NeuroGuard</span>
            <span className="text-xs text-teal-100">SPIT PDS Project</span>
          </span>
        </Link>
        <nav className="mt-8 space-y-2">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-teal-50 hover:bg-white/10"
            >
              <item.icon size={18} />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="absolute bottom-5 left-5 right-5 space-y-2">
          <Link
            href="/dashboard/counsellor#alerts"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-teal-50 hover:bg-white/10"
          >
            <Bell size={18} />
            Alerts
          </Link>
          <button
            suppressHydrationWarning
            type="button"
            onClick={logout}
            className="focus-ring flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-teal-50 hover:bg-white/10"
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-[#dce7e2] bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
          <Link href="/dashboard/student" className="font-semibold">
            NeuroGuard
          </Link>
          <div className="flex gap-2">
            {nav.map((item) => (
              <Link key={item.href} href={item.href} className="rounded-md p-2 text-[#58706a]">
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
