create extension if not exists pgcrypto;

create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  role text check (role in ('OFFICER', 'SUPERVISOR')) not null,
  created_at timestamp default now()
);

create table system_settings (
  id uuid primary key default gen_random_uuid(),
  interest_type text check (interest_type in ('SIMPLE', 'COMPOUND')) not null,
  penalty_percent numeric(5,2) default 1.00,
  default_interest_rates jsonb not null default '{}'::jsonb,
  updated_at timestamp default now()
);

insert into system_settings (interest_type, penalty_percent)
values ('SIMPLE', 1.00);

create table customers (
  id uuid primary key default gen_random_uuid(),
  customer_code text unique not null,
  full_name text not null,
  id_type text not null,
  id_number text unique not null,
  created_at timestamp default now()
);

create table fixed_deposits (
  id uuid primary key default gen_random_uuid(),
  fd_number text unique not null,

  customer_id uuid references customers(id),

  customer_name text not null,
  id_type text not null,
  id_number text not null,

  deposit_amount numeric(15,2) not null check (deposit_amount > 0),
  interest_rate numeric(5,2) not null check (interest_rate >= 0 and interest_rate <= 20),

  tenure_months integer not null check (tenure_months > 0),
  start_date date not null,

  maturity_date date not null,
  maturity_amount numeric(15,2) not null,

  closed_at date,

  status text check (status in ('ACTIVE', 'CLOSED')) default 'ACTIVE',

  created_by uuid references users(id),
  created_at timestamp default now()
);

create table customer_ai_profiles (
  customer_id uuid primary key references customers(id),
  last_risk_score integer not null,
  last_analysis_date timestamp not null default now(),
  loyalty_score integer not null,
  penalty_reduction_percent numeric(5,2) not null default 0.00
);

-- Lock further edits once CLOSED (works regardless of RLS/auth approach)
create or replace function public.prevent_update_when_closed()
returns trigger
language plpgsql
as $$
begin
  if old.status = 'CLOSED' then
    raise exception 'FD is CLOSED and cannot be modified';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_prevent_update_when_closed on public.fixed_deposits;

create trigger trg_prevent_update_when_closed
before update on public.fixed_deposits
for each row
execute function public.prevent_update_when_closed();

-- Optional: updated_at maintenance
create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_touch_system_settings_updated_at on public.system_settings;

create trigger trg_touch_system_settings_updated_at
before update on public.system_settings
for each row
execute function public.touch_updated_at();

-- RLS recommendation for custom-auth-only approach:
-- Enable RLS and DO NOT add policies (so anon/authenticated keys cannot access tables directly).
-- Backend uses service role key (bypasses RLS) for all DB operations.
alter table users enable row level security;
alter table system_settings enable row level security;
alter table customers enable row level security;
alter table fixed_deposits enable row level security;
alter table customer_ai_profiles enable row level security;

create or replace function public.authenticate_user(p_email text, p_password text)
returns table (
  id uuid,
  email text,
  role text
)
language sql
security definer
as $$
  select u.id, u.email, u.role
  from public.users u
  where u.email = p_email
    and u.password_hash = crypt(p_password, u.password_hash)
  limit 1;
$$;
