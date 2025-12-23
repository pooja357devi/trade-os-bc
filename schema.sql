(Database Structure - BC Optimized)
-- Enable UUIDs
create extension if not exists "uuid-ossp";

-- 1. CLIENTS (Business Owners across BC)
create table clients (
  id uuid default uuid_generate_v4() primary key,
  business_name text not null,
  phone_number text not null unique,
  twilio_number_sid text,
  owner_email text,
  city text default 'Vancouver',      -- Updated default for BC
  timezone text default 'America/Vancouver', -- Covers 95% of BC
  industry_type text default 'general',

  -- BILLING & LIABILITY
  payment_status text default 'active',
  stripe_account_id text,
  terms_agreed_at timestamp with time zone,

  -- SECURITY
  admin_password text default 'change_me_now',
  session_token text default uuid_generate_v4(),
  created_at timestamp with time zone default now()
);

-- 2. LEADS (Customers)
create table leads (
  id uuid default uuid_generate_v4() primary key,
  client_id uuid references clients(id),
  customer_phone text not null,
  status text default 'New',
  consent_status text default 'implied',
  conversation_history text default '',
  last_message_sid text,
  ai_paused_until timestamp with time zone,
  created_at timestamp with time zone default now()
);

-- 3. INDUSTRY CONFIGS (The Brains)
create table industry_configs (
  industry_type text primary key,
  system_prompt_template text,
  safety_keywords text[],
  safety_response text,
  vision_instruction text
);

-- 4. LOGS & EVIDENCE
create table compliance_logs (
  id uuid default uuid_generate_v4() primary key,
  client_id uuid references clients(id),
  violation_type text,
  content text,
  timestamp timestamp with time zone default now()
);

create table evidence (
  id uuid default uuid_generate_v4() primary key,
  client_id uuid references clients(id),
  lead_phone text,
  storage_url text,
  created_at timestamp with time zone default now()
);

create table usage_logs (
  id uuid default uuid_generate_v4() primary key,
  client_id uuid references clients(id),
  tokens int,
  cost_est numeric,
  created_at timestamp with time zone default now()
);

-- 5. SEED DATA (BC Wide Rules)
insert into industry_configs (industry_type, system_prompt_template, safety_keywords, safety_response) values
('towing', 'CRITICAL: User is on highway (Hwy 1, Coquihalla, etc). INSTRUCT TO STAY IN CAR. Ask if Property Owner for impounds.', ARRAY['highway', 'freeway', 'coquihalla'], 'STAY IN CAR'),
('plumber', 'Ask Year Built if cutting walls (WorkSafeBC Asbestos). Ask Gas/Electric for heaters (Technical Safety BC).', ARRAY['gas', 'smell', 'rotten'], 'DANGER: Call FortisBC (1-800-663-9911)'),
('pest_control', 'NEVER give DIY chemical advice. Ask if Owner/Renter (BC Tenancy Act). Refer Wildlife to Trappers.', ARRAY['bleach', 'poison', 'mix'], 'We do not recommend DIY chemicals. Safety first.');
