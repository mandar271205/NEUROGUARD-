create table if not exists public.students (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text unique,
  counsellor_id uuid not null references auth.users(id) on delete cascade,
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
  model_type text not null check (model_type in ('tabular_rf', 'audio_mlp', 'fusion_gb')),
  prediction_class integer not null check (prediction_class in (0, 1, 2)),
  confidence double precision not null check (confidence >= 0 and confidence <= 1),
  probabilities jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists students_counsellor_id_idx on public.students(counsellor_id);
create index if not exists surveys_student_id_created_at_idx on public.surveys(student_id, created_at desc);
create index if not exists predictions_student_id_created_at_idx on public.predictions(student_id, created_at desc);
create index if not exists predictions_high_risk_idx on public.predictions(prediction_class) where prediction_class = 2;
create index if not exists audio_files_student_id_created_at_idx on public.audio_files(student_id, created_at desc);

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

drop policy if exists "Counsellors can read assigned students" on public.students;
create policy "Counsellors can read assigned students"
on public.students for select
to authenticated
using (counsellor_id = auth.uid());

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
