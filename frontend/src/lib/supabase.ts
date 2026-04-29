"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { hasSupabaseConfig, supabaseAnonKey, supabaseUrl } from "@/lib/config";

let client: SupabaseClient | null = null;

export function getSupabase() {
  if (!hasSupabaseConfig()) return null;
  if (!client) {
    client = createClient(supabaseUrl, supabaseAnonKey);
  }
  return client;
}
