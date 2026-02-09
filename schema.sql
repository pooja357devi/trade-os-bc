-- =====================================================
-- FINAL MULTI-TENANT DATABASE STRUCTURE (USER TABLE + GLOBAL INDUSTRY CONFIG)
-- Trade-OS-BC SaaS Structure
-- =====================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- =====================================================
-- 1. CLIENTS = COMPANIES / TENANTS
-- =====================================================
CREATE TABLE IF NOT EXISTS clients (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  business_name TEXT NOT NULL,
  phone_number TEXT UNIQUE NOT NULL,
  twilio_number_sid TEXT,
  owner_email TEXT,
  city TEXT DEFAULT 'Vancouver',
  timezone TEXT DEFAULT 'America/Vancouver',
  industry_type TEXT DEFAULT 'general',

  payment_status TEXT DEFAULT 'active',
  stripe_account_id TEXT,
  terms_agreed_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ
);


-- =====================================================
-- 2. USERS (LOGIN SYSTEM)
-- Multiple users per company
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
  user_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  username TEXT NOT NULL,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'user',

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ
);

-- Same email allowed in different companies
CREATE UNIQUE INDEX IF NOT EXISTS users_client_email_unique
ON users (client_id, lower(email));


-- =====================================================
-- 3. LEADS / CUSTOMERS
-- Tenant isolated
-- =====================================================
CREATE TABLE IF NOT EXISTS leads (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  customer_phone TEXT NOT NULL,
  status TEXT DEFAULT 'New',
  consent_status TEXT DEFAULT 'implied',
  conversation_history TEXT DEFAULT '',
  last_message_sid TEXT,
  ai_paused_until TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ
);


-- =====================================================
-- 4. INDUSTRY CONFIG (GLOBAL VERSION - prev schema)
-- =====================================================
DROP TABLE IF EXISTS industry_configs;

CREATE TABLE industry_configs (
    industry_type TEXT PRIMARY KEY,
    system_prompt_template TEXT,
    safety_keywords TEXT[],
    safety_response TEXT,
    vision_instruction TEXT
);

-- Default / Seed Data
INSERT INTO industry_configs (industry_type, system_prompt_template, safety_keywords, safety_response)
VALUES
('towing', 'CRITICAL: Stay in car on highway.', ARRAY['highway','freeway'], 'STAY IN CAR'),
('plumber', 'Ask about gas leaks.', ARRAY['gas','smell'], 'Call emergency gas service'),
('pest_control', 'No DIY chemical advice.', ARRAY['poison','bleach'], 'Use professional service')
ON CONFLICT (industry_type) DO NOTHING;


-- =====================================================
-- 5. LOGGING / COMPLIANCE / BILLING
-- =====================================================
CREATE TABLE IF NOT EXISTS compliance_logs (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  violation_type TEXT,
  content TEXT,
  timestamp TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evidence (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  lead_phone TEXT,
  storage_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usage_logs (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  tokens INT,
  cost_est NUMERIC,
  created_at TIMESTAMPTZ DEFAULT now()
);


-- =====================================================
-- PERFORMANCE INDEXES
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_leads_client_phone
ON leads (client_id, customer_phone);

CREATE INDEX IF NOT EXISTS idx_usage_client
ON usage_logs (client_id);

CREATE INDEX IF NOT EXISTS idx_evidence_client
ON evidence (client_id);


-- 5. SEED DATA (BC Wide Rules)
insert into industry_configs (industry_type, system_prompt_template, safety_keywords, safety_response) values
('towing', 'CRITICAL: User is on highway (Hwy 1, Coquihalla, etc). INSTRUCT TO STAY IN CAR. Ask if Property Owner for impounds.', ARRAY['highway', 'freeway', 'coquihalla'], 'STAY IN CAR'),
('plumber', 'Ask Year Built if cutting walls (WorkSafeBC Asbestos). Ask Gas/Electric for heaters (Technical Safety BC).', ARRAY['gas', 'smell', 'rotten'], 'DANGER: Call FortisBC (1-800-663-9911)'),
('pest_control', 'NEVER give DIY chemical advice. Ask if Owner/Renter (BC Tenancy Act). Refer Wildlife to Trappers.', ARRAY['bleach', 'poison', 'mix'], 'We do not recommend DIY chemicals. Safety first.');
