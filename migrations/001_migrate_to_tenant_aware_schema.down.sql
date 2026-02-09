-- Migration: 001_migrate_to_tenant_aware_schema
-- Direction: DOWN (Rollback changes)
-- Date: 2026-02-06
-- Purpose: Revert to original schema (use only if migration caused issues)

-- WARNING: This rollback will lose any client-specific configs created after migration.
-- Backup your data before rolling back.

-- Step 1: Drop new indexes
DROP INDEX IF EXISTS idx_leads_client_phone;
DROP INDEX IF EXISTS idx_usage_client;
DROP INDEX IF EXISTS idx_evidence_client;
DROP INDEX IF EXISTS idx_compliance_client;
DROP INDEX IF EXISTS users_client_email_unique;
DROP INDEX IF EXISTS industry_client_unique;

-- Step 2: Restore global unique constraint on users.email
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_client_email_unique;
CREATE UNIQUE INDEX IF NOT EXISTS users_email_key ON users (lower(email));

-- Step 3: Remove ON DELETE CASCADE and revert to nullable client_id
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_client_id_fkey;
ALTER TABLE users ADD CONSTRAINT users_client_id_fkey 
  FOREIGN KEY (client_id) REFERENCES clients(id);
ALTER TABLE users ALTER COLUMN client_id DROP NOT NULL;

-- Step 4: Revert foreign keys on other tables (nullable, no cascade)
ALTER TABLE leads DROP CONSTRAINT IF EXISTS leads_client_id_fkey;
ALTER TABLE leads ADD CONSTRAINT leads_client_id_fkey 
  FOREIGN KEY (client_id) REFERENCES clients(id);
ALTER TABLE leads ALTER COLUMN client_id DROP NOT NULL;

ALTER TABLE compliance_logs DROP CONSTRAINT IF EXISTS compliance_logs_client_id_fkey;
ALTER TABLE compliance_logs ADD CONSTRAINT compliance_logs_client_id_fkey 
  FOREIGN KEY (client_id) REFERENCES clients(id);
ALTER TABLE compliance_logs ALTER COLUMN client_id DROP NOT NULL;

ALTER TABLE evidence DROP CONSTRAINT IF EXISTS evidence_client_id_fkey;
ALTER TABLE evidence ADD CONSTRAINT evidence_client_id_fkey 
  FOREIGN KEY (client_id) REFERENCES clients(id);
ALTER TABLE evidence ALTER COLUMN client_id DROP NOT NULL;

ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS usage_logs_client_id_fkey;
ALTER TABLE usage_logs ADD CONSTRAINT usage_logs_client_id_fkey 
  FOREIGN KEY (client_id) REFERENCES clients(id);
ALTER TABLE usage_logs ALTER COLUMN client_id DROP NOT NULL;

-- Step 5: Remove audit columns (optional; you can keep these)
-- ALTER TABLE users DROP COLUMN IF EXISTS updated_at;
-- ALTER TABLE leads DROP COLUMN IF EXISTS updated_at;
-- ALTER TABLE clients DROP COLUMN IF EXISTS updated_at;

-- Step 6: Restore industry_configs to original structure
-- This is complex and may lose client-specific configs.
-- If you want to preserve client_id and updated_at, comment out the next lines.

-- WARNING: Uncommenting the next block will DELETE all client-specific industry configs!
-- ALTER TABLE industry_configs DROP CONSTRAINT IF EXISTS industry_client_unique;
-- ALTER TABLE industry_configs DROP COLUMN IF EXISTS id CASCADE;
-- ALTER TABLE industry_configs DROP COLUMN IF EXISTS client_id;
-- ALTER TABLE industry_configs DROP COLUMN IF EXISTS created_at;
-- ALTER TABLE industry_configs DROP COLUMN IF EXISTS updated_at;
-- ALTER TABLE industry_configs ADD CONSTRAINT industry_configs_pkey PRIMARY KEY (industry_type);

-- Step 7: Restore plaintext secrets to clients (optional; NOT RECOMMENDED)
-- If you want to restore admin_password and session_token, uncomment:
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS admin_password text default 'change_me_now';
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS session_token text default uuid_generate_v4();

-- Rollback complete. Review dashboard.py changes manually as needed.
