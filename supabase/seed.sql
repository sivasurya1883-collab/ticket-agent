-- Seed / mock data for local testing
-- Run AFTER schema.sql

-- 1) Users (bcrypt hashes generated in DB using pgcrypto)
-- Password for all users below: Password@123
insert into public.users (email, password_hash, role)
values
  ('officer1@bank.local', crypt('Password@123', gen_salt('bf')), 'OFFICER'),
  ('officer2@bank.local', crypt('Password@123', gen_salt('bf')), 'OFFICER'),
  ('supervisor1@bank.local', crypt('Password@123', gen_salt('bf')), 'SUPERVISOR')
on conflict (email) do update
set role = excluded.role,
    password_hash = excluded.password_hash;

-- 2) System settings
-- Keep a single active row by updating the most recently updated record.
update public.system_settings
set interest_type = 'SIMPLE',
    penalty_percent = 1.00,
    default_interest_rates = '{"6": 6.50, "12": 7.00, "24": 6.75, "36": 7.25, "60": 7.50}'::jsonb,
    updated_at = now()
where id = (
  select id
  from public.system_settings
  order by updated_at desc
  limit 1
);

-- 3) Customers
insert into public.customers (customer_code, full_name, id_type, id_number)
values
  ('CUST-0001', 'Aarav Sharma', 'PAN', 'ABCDE1234F'),
  ('CUST-0002', 'Meera Iyer', 'AADHAAR', '1234-5678-9012'),
  ('CUST-0003', 'Rohan Gupta', 'PAN', 'PQRSX9876K'),
  ('CUST-0004', 'Sara Khan', 'PASSPORT', 'M1234567')
on conflict (id_number) do update
set full_name = excluded.full_name,
    customer_code = excluded.customer_code,
    id_type = excluded.id_type;

-- 4) Fixed deposits
-- Create some mock FDs for testing register, filters, and closure.
with u as (
  select id as officer1_id from public.users where email = 'officer1@bank.local'
), v as (
  select id as officer2_id from public.users where email = 'officer2@bank.local'
), c1 as (
  select id as customer_id from public.customers where id_number = 'ABCDE1234F'
), c2 as (
  select id as customer_id from public.customers where id_number = '1234-5678-9012'
), c3 as (
  select id as customer_id from public.customers where id_number = 'PQRSX9876K'
), c4 as (
  select id as customer_id from public.customers where id_number = 'M1234567'
)
insert into public.fixed_deposits (
  fd_number,
  customer_id,
  customer_name,
  id_type,
  id_number,
  deposit_amount,
  interest_rate,
  tenure_months,
  start_date,
  maturity_date,
  maturity_amount,
  closed_at,
  status,
  created_by
)
values
  (
    'FD-2026-0001',
    (select customer_id from c1),
    'Aarav Sharma',
    'PAN',
    'ABCDE1234F',
    100000.00,
    7.50,
    12,
    '2026-01-15',
    '2027-01-15',
    107500.00,
    null,
    'ACTIVE',
    (select officer1_id from u)
  ),
  (
    'FD-2026-0002',
    (select customer_id from c2),
    'Meera Iyer',
    'AADHAAR',
    '1234-5678-9012',
    250000.00,
    6.75,
    24,
    '2026-02-01',
    '2028-02-01',
    283750.00,
    null,
    'ACTIVE',
    (select officer2_id from v)
  ),
  (
    'FD-2025-0003',
    (select customer_id from c3),
    'Rohan Gupta',
    'PAN',
    'PQRSX9876K',
    50000.00,
    8.00,
    6,
    '2025-10-10',
    '2026-04-10',
    52000.00,
    '2026-02-01',
    'CLOSED',
    (select officer1_id from u)
  ),
  (
    'FD-2026-0004',
    (select customer_id from c4),
    'Sara Khan',
    'PASSPORT',
    'M1234567',
    150000.00,
    7.25,
    36,
    '2026-03-05',
    '2029-03-05',
    182625.00,
    null,
    'ACTIVE',
    (select officer2_id from v)
  )
on conflict (fd_number) do nothing;

-- 5) Customer AI profiles (sample)
insert into public.customer_ai_profiles (customer_id, last_risk_score, loyalty_score, penalty_reduction_percent)
values
  ((select id from public.customers where id_number = 'ABCDE1234F'), 28, 86, 0.50),
  ((select id from public.customers where id_number = '1234-5678-9012'), 42, 72, 0.50),
  ((select id from public.customers where id_number = 'PQRSX9876K'), 68, 45, 0.00),
  ((select id from public.customers where id_number = 'M1234567'), 35, 78, 0.50)
on conflict (customer_id) do update
set last_risk_score = excluded.last_risk_score,
    last_analysis_date = now(),
    loyalty_score = excluded.loyalty_score,
    penalty_reduction_percent = excluded.penalty_reduction_percent;
