create table if not exists public.students (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text unique,
  counsellor_id uuid references auth.users(id) on delete set null,
  enrollment_year integer,
  created_at timestamptz not null default now()
);

create table if not exists public.surveys (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  responses jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists public.audio_files (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  file_path text not null,
  extracted_features jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists public.predictions (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  survey_id uuid references public.surveys(id) on delete set null,
  audio_id uuid references public.audio_files(id) on delete set null,
  model_type text not null check (model_type in ('tabular_rf', 'audio_mlp', 'fusion_gb', 'stress_voice_combined')),
  prediction_class integer not null check (prediction_class in (0, 1, 2)),
  confidence double precision not null check (confidence >= 0 and confidence <= 1),
  probabilities jsonb not null default '{}'::jsonb,
  risk_level text check (risk_level in ('low', 'moderate', 'high')),
  audit_hash text,
  created_at timestamptz not null default now()
);

alter table public.predictions
  add column if not exists risk_level text check (risk_level in ('low', 'moderate', 'high'));

alter table public.predictions
  add column if not exists audit_hash text;

do $$
begin
  alter table public.predictions drop constraint if exists predictions_model_type_check;
  alter table public.predictions
    add constraint predictions_model_type_check
    check (model_type in ('tabular_rf', 'audio_mlp', 'fusion_gb', 'stress_voice_combined'));
end $$;

create table if not exists public.voice_enrolments (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  z_vector jsonb not null,
  sample_count integer not null check (sample_count > 0),
  audio_hashes jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.consent_logs (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  data_collection boolean not null default true,
  ml_processing boolean not null default true,
  zk_fl boolean not null default true,
  raw_audio_storage boolean not null default false,
  expires_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.audit_events (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  prediction_id uuid references public.predictions(id) on delete set null,
  event_type text not null,
  stress_score double precision not null check (stress_score >= 0 and stress_score <= 1),
  audit_hash text not null,
  zk_proof_hash text,
  contract_tx_hash text,
  created_at timestamptz not null default now()
);

create index if not exists students_counsellor_id_idx on public.students(counsellor_id);
create index if not exists surveys_student_id_created_at_idx on public.surveys(student_id, created_at desc);
create index if not exists predictions_student_id_created_at_idx on public.predictions(student_id, created_at desc);
create index if not exists predictions_high_risk_idx on public.predictions(prediction_class) where prediction_class = 2;
create index if not exists audio_files_student_id_created_at_idx on public.audio_files(student_id, created_at desc);
create index if not exists voice_enrolments_student_id_created_at_idx on public.voice_enrolments(student_id, created_at desc);
create index if not exists consent_logs_student_id_created_at_idx on public.consent_logs(student_id, created_at desc);
create index if not exists audit_events_student_id_created_at_idx on public.audit_events(student_id, created_at desc);

do $$
begin
  begin
    alter publication supabase_realtime add table public.predictions;
  exception
    when duplicate_object then null;
    when undefined_object then null;
  end;
end $$;

alter table public.students enable row level security;
alter table public.surveys enable row level security;
alter table public.audio_files enable row level security;
alter table public.predictions enable row level security;
alter table public.voice_enrolments enable row level security;
alter table public.consent_logs enable row level security;
alter table public.audit_events enable row level security;

drop policy if exists "Counsellors can read assigned students" on public.students;
create policy "Counsellors can read assigned students"
on public.students for select
to authenticated
using (counsellor_id = auth.uid() or id = auth.uid());

drop policy if exists "Counsellors can read assigned surveys" on public.surveys;
create policy "Counsellors can read assigned surveys"
on public.surveys for select
to authenticated
using (
  exists (
    select 1 from public.students s
    where s.id = surveys.student_id
      and s.counsellor_id = auth.uid()
  )
);

drop policy if exists "Counsellors can read assigned predictions" on public.predictions;
create policy "Counsellors can read assigned predictions"
on public.predictions for select
to authenticated
using (
  exists (
    select 1 from public.students s
    where s.id = predictions.student_id
      and s.counsellor_id = auth.uid()
  )
);

drop policy if exists "Counsellors can read assigned audio files" on public.audio_files;
create policy "Counsellors can read assigned audio files"
on public.audio_files for select
to authenticated
using (
  exists (
    select 1 from public.students s
    where s.id = audio_files.student_id
      and s.counsellor_id = auth.uid()
  )
);

drop policy if exists "Students can read own voice enrolments" on public.voice_enrolments;
create policy "Students can read own voice enrolments"
on public.voice_enrolments for select
to authenticated
using (student_id = auth.uid());

drop policy if exists "Counsellors can read assigned voice enrolments" on public.voice_enrolments;
create policy "Counsellors can read assigned voice enrolments"
on public.voice_enrolments for select
to authenticated
using (
  exists (
    select 1 from public.students s
    where s.id = voice_enrolments.student_id
      and s.counsellor_id = auth.uid()
  )
);

drop policy if exists "Students can read own consent logs" on public.consent_logs;
create policy "Students can read own consent logs"
on public.consent_logs for select
to authenticated
using (student_id = auth.uid());

drop policy if exists "Students can read own audit events" on public.audit_events;
create policy "Students can read own audit events"
on public.audit_events for select
to authenticated
using (student_id = auth.uid());

drop policy if exists "Counsellors can read assigned audit events" on public.audit_events;
create policy "Counsellors can read assigned audit events"
on public.audit_events for select
to authenticated
using (
  exists (
    select 1 from public.students s
    where s.id = audit_events.student_id
      and s.counsellor_id = auth.uid()
  )
);

drop policy if exists "Service role can manage students" on public.students;
create policy "Service role can manage students"
on public.students for all
to service_role
using (true)
with check (true);

drop policy if exists "Service role can manage surveys" on public.surveys;
create policy "Service role can manage surveys"
on public.surveys for all
to service_role
using (true)
with check (true);

drop policy if exists "Service role can manage predictions" on public.predictions;
create policy "Service role can manage predictions"
on public.predictions for all
to service_role
using (true)
with check (true);

drop policy if exists "Service role can manage audio files" on public.audio_files;
create policy "Service role can manage audio files"
on public.audio_files for all
to service_role
using (true)
with check (true);

drop policy if exists "Service role can manage voice enrolments" on public.voice_enrolments;
create policy "Service role can manage voice enrolments"
on public.voice_enrolments for all
to service_role
using (true)
with check (true);

drop policy if exists "Service role can manage consent logs" on public.consent_logs;
create policy "Service role can manage consent logs"
on public.consent_logs for all
to service_role
using (true)
with check (true);

drop policy if exists "Service role can manage audit events" on public.audit_events;
create policy "Service role can manage audit events"
on public.audit_events for all
to service_role
using (true)
with check (true);
