create extension if not exists "uuid-ossp";

create type public.ops_role as enum ('founder', 'dev', 'risk', 'compliance_ops', 'trader', 'auditor');
create type public.signal_source as enum ('BEEP', 'PineScript', 'EMA', 'price_action', 'python_algo');
create type public.signal_status as enum ('DRAFT', 'SUBMITTED', 'REVIEWING', 'VERIFIED', 'PUBLISHED', 'EXPIRED', 'REJECTED', 'CANCELLED', 'RETRACTED');
create type public.signal_action as enum ('BUY', 'SELL');

create table if not exists public.ops_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null,
  role public.ops_role not null default 'trader',
  auditor_expires_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.signal_submissions (
  id uuid primary key default uuid_generate_v4(),
  symbol text not null,
  timeframe text not null,
  action public.signal_action not null,
  entry numeric not null,
  stop_loss numeric not null,
  take_profit numeric not null,
  source public.signal_source not null,
  strategy_version text not null,
  screenshot_url text,
  rationale text not null,
  submitted_by uuid not null references public.ops_profiles(id),
  status public.signal_status not null default 'SUBMITTED',
  expires_at timestamptz not null,
  rejection_reason text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint signal_submission_prices check (entry <> stop_loss and entry <> take_profit and stop_loss <> take_profit)
);

create table if not exists public.signal_reviews (
  id uuid primary key default uuid_generate_v4(),
  signal_id uuid not null references public.signal_submissions(id) on delete cascade,
  reviewer_id uuid not null references public.ops_profiles(id),
  decision public.signal_status not null,
  gate_results jsonb not null default '{}'::jsonb,
  notes text,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists signal_submissions_status_idx on public.signal_submissions(status, created_at desc);
create index if not exists signal_submissions_expiry_idx on public.signal_submissions(expires_at);
create index if not exists signal_reviews_signal_idx on public.signal_reviews(signal_id, created_at desc);

create or replace function public.current_ops_role()
returns public.ops_role
language sql
stable
security definer
set search_path = public
as $$
  select role from public.ops_profiles where id = auth.uid();
$$;

create or replace function public.is_active_auditor()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select public.current_ops_role() = 'auditor'
    and exists (
      select 1 from public.ops_profiles
      where id = auth.uid()
        and auditor_expires_at is not null
        and auditor_expires_at > timezone('utc', now())
    );
$$;

alter table public.ops_profiles enable row level security;
alter table public.signal_submissions enable row level security;
alter table public.signal_reviews enable row level security;

create policy "ops profiles self or founder read"
on public.ops_profiles for select
using (id = auth.uid() or public.current_ops_role() = 'founder');

create policy "founder manages ops profiles"
on public.ops_profiles for all
using (public.current_ops_role() = 'founder')
with check (public.current_ops_role() = 'founder');

create policy "staff read signal submissions"
on public.signal_submissions for select
using (
  public.current_ops_role() in ('founder', 'dev', 'risk', 'compliance_ops', 'auditor')
  or (public.current_ops_role() = 'trader' and submitted_by = auth.uid())
);

create policy "traders submit signals"
on public.signal_submissions for insert
with check (public.current_ops_role() in ('founder', 'dev', 'trader') and submitted_by = auth.uid());

create policy "reviewers transition signals"
on public.signal_submissions for update
using (public.current_ops_role() in ('founder', 'dev', 'risk'))
with check (public.current_ops_role() in ('founder', 'dev', 'risk'));

create policy "staff read reviews"
on public.signal_reviews for select
using (public.current_ops_role() in ('founder', 'dev', 'risk', 'compliance_ops', 'auditor'));

create policy "authorized reviewers write reviews"
on public.signal_reviews for insert
with check (public.current_ops_role() in ('founder', 'dev', 'risk') and reviewer_id = auth.uid());

comment on table public.signal_submissions is 'Human-in-the-loop signal intake; never direct subscriber publication or MT5 execution.';
comment on table public.signal_reviews is 'Immutable review evidence for signal verification decisions.';
