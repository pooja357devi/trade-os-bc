-- Migration: 001_migrate_to_tenant_aware_schema
-- Direction: UP (Apply changes to make schema multi-tenant safe)
-- Date: 2026-02-06
-- Purpose: Harden schema for multi-tenant isolation, add client-scoped configs, remove plaintext secrets

-- Step 1: Drop unsafe global unique constraint on users.email
-- This allows the same email to exist across different tenants
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;

-- Step 2: Make users.client_id NOT NULL (if there are NULL rows, update them first)
-- If you have existing rows with NULL client_id, you must set them to a valid client_id first
ALTER TABLE users ALTER COLUMN client_id SET NOT NULL;

-- Step 3: Add ON DELETE CASCADE to users.client_id foreign key
-- This ensures users are deleted when their client is deleted
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_client_id_fkey;
ALTER TABLE users ADD CONSTRAINT users_client_id_fkey 
  FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE;

-- Step 4: Create composite unique index (client_id, email) for per-tenant uniqueness
CREATE UNIQUE INDEX IF NOT EXISTS users_client_email_unique 
  ON users (client_id, lower(email));

-- Step 5: Make leads.client_id NOT NULL and add ON DELETE CASCADE
ALTER TABLE leads ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE leads DROP CONSTRAINT IF EXISTS leads_client_id_fkey;
ALTER TABLE leads ADD CONSTRAINT leads_client_id_fkey 
  FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE;

-- Step 6: Make compliance_logs.client_id NOT NULL and add ON DELETE CASCADE
ALTER TABLE compliance_logs ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE compliance_logs DROP CONSTRAINT IF EXISTS compliance_logs_client_id_fkey;
ALTER TABLE compliance_logs ADD CONSTRAINT compliance_logs_client_id_fkey 
  FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE;

-- Step 7: Make evidence.client_id NOT NULL and add ON DELETE CASCADE
ALTER TABLE evidence ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE evidence DROP CONSTRAINT IF EXISTS evidence_client_id_fkey;
ALTER TABLE evidence ADD CONSTRAINT evidence_client_id_fkey 
  FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE;

-- Step 8: Make usage_logs.client_id NOT NULL and add ON DELETE CASCADE
ALTER TABLE usage_logs ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS usage_logs_client_id_fkey;
ALTER TABLE usage_logs ADD CONSTRAINT usage_logs_client_id_fkey 
  FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE;

-- Step 9: Add performance indexes
CREATE INDEX IF NOT EXISTS idx_leads_client_phone 
  ON leads (client_id, customer_phone);
CREATE INDEX IF NOT EXISTS idx_usage_client 
  ON usage_logs (client_id);
CREATE INDEX IF NOT EXISTS idx_evidence_client 
  ON evidence (client_id);
CREATE INDEX IF NOT EXISTS idx_compliance_client 
  ON compliance_logs (client_id);

-- Step 10: Add audit columns to key tables
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at timestamptz;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS updated_at timestamptz;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS updated_at timestamptz;

-- Step 11: Upgrade clients table and remove plaintext secrets
-- Remove unsafe default and plaintext password column
ALTER TABLE clients DROP COLUMN IF EXISTS admin_password;
ALTER TABLE clients DROP COLUMN IF EXISTS session_token;

-- Ensure clients has audit timestamps
ALTER TABLE clients ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE clients ADD COLUMN IF NOT EXISTS updated_at timestamptz;

-- Step 12: Alter industry_configs to support client-specific overrides
-- Add id and client_id columns if they don't exist
ALTER TABLE industry_configs ADD COLUMN IF NOT EXISTS id uuid default uuid_generate_v4() PRIMARY KEY;
ALTER TABLE industry_configs ADD COLUMN IF NOT EXISTS client_id uuid REFERENCES clients(id) ON DELETE CASCADE;
ALTER TABLE industry_configs ADD COLUMN IF NOT EXISTS created_at timestamptz default now();
ALTER TABLE industry_configs ADD COLUMN IF NOT EXISTS updated_at timestamptz;

-- Drop old primary key (industry_type only) if it exists
ALTER TABLE industry_configs DROP CONSTRAINT IF EXISTS industry_configs_pkey;

-- Create new unique index to allow global defaults (client_id = NULL) and per-client overrides
CREATE UNIQUE INDEX IF NOT EXISTS industry_client_unique 
  ON industry_configs (client_id, industry_type);

-- Step 13: Ensure seed data is global (client_id = NULL)
-- This upsert pattern will insert if missing or do nothing if already exists
INSERT INTO industry_configs (client_id, industry_type, system_prompt_template, safety_keywords, safety_response)
VALUES
(NULL, 'towing', 'CRITICAL: User is on highway (Hwy 1, Coquihala, etc). INSTRUCT TO STAY IN CAR. Ask if Property Owner for impounds.', ARRAY['highway', 'freeway', 'coquihala'], 'STAY IN CAR'),
(NULL, 'plumber', 'Ask Year Built if cutting walls (WorkSafeBC Asbestos). Ask Gas/Electric for heaters (Technical Safety BC).', ARRAY['gas', 'smell', 'rotten'], 'DANGER: Call FortisBC (1-800-663-9911)'),
(NULL, 'pest_control', 'NEVER give DIY chemical advice. Ask if Owner/Renter (BC Tenancy Act). Refer Wildlife to Trappers.', ARRAY['bleach', 'poison', 'mix'], 'We do not recommend DIY chemicals. Safety first.')
ON CONFLICT (client_id, industry_type) DO NOTHING;

-- Step 14: Summary comment
-- Migration complete. Key changes:
-- 1) users.email is now per-tenant (composite index on client_id, email)
-- 2) All business data tables have NOT NULL client_id with ON DELETE CASCADE
-- 3) industry_configs supports global defaults + client-specific overrides
-- 4) Performance indexes added for client_id lookups
-- 5) Plaintext secrets removed from clients table
-- 6) Audit timestamps added to key tables
--
-- NOTE: If you have existing NULL client_id rows in any table, 
-- update them BEFORE applying this migration.
