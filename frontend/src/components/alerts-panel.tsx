"use client";

import { useEffect, useState } from "react";
import { BellRing } from "lucide-react";
import { getSupabase } from "@/lib/supabase";
import { RiskBadge } from "@/components/risk-badge";

type AlertRow = {
  id?: string;
  student_id?: string;
  prediction_class?: number;
  confidence?: number;
  created_at?: string;
};

export function AlertsPanel() {
  const [alerts, setAlerts] = useState<AlertRow[]>([]);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) return;
    const channel = supabase
      .channel("neuroguard-high-risk-alerts")
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "predictions",
          filter: "prediction_class=eq.2"
        },
        (payload) => {
          setAlerts((current) => [payload.new as AlertRow, ...current].slice(0, 8));
        }
      )
      .subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }, []);

  return (
    <section id="alerts" className="rounded-lg border border-[#dce7e2] bg-white p-5">
      <div className="mb-4 flex items-center gap-2">
        <BellRing size={18} className="text-[#d95d39]" />
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#58706a]">Realtime alerts</h2>
      </div>
      {alerts.length ? (
        <div className="space-y-3">
          {alerts.map((alert, index) => (
            <div key={alert.id || index} className="rounded-md border border-rose-100 bg-rose-50 p-3">
              <div className="flex items-center justify-between gap-3">
                <RiskBadge level={alert.prediction_class} />
                <span className="font-mono text-xs text-rose-900">
                  {Math.round(Number(alert.confidence || 0) * 100)}%
                </span>
              </div>
              <p className="mt-2 text-xs text-rose-900">Student: {alert.student_id || "unknown"}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-[#58706a]">No high-risk events received in this session.</p>
      )}
    </section>
  );
}
