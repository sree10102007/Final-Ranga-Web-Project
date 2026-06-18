-- PostgreSQL Least Privilege Database Roles Setup Script
-- Run this script as a superuser/administrator on your production database.

-- 1. Create Roles (without login privileges by default, can be granted to specific users)
CREATE ROLE readonly_user;
CREATE ROLE reporting_user;
CREATE ROLE application_user;
CREATE ROLE admin_user;

-- 2. Revoke all default privileges from public schema to secure the database
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO PUBLIC;

-- 3. Grant READONLY_USER permissions (SELECT only on all existing/future tables)
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

-- 4. Grant REPORTING_USER permissions (SELECT on reports, sales, expenses, and finances)
GRANT USAGE ON SCHEMA public TO reporting_user;
GRANT SELECT ON TABLE sales_records, other_sales_records, expenses, finances, reports TO reporting_user;

-- 5. Grant APPLICATION_USER permissions (SELECT, INSERT, UPDATE, DELETE on all operational tables)
GRANT USAGE ON SCHEMA public TO application_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO application_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO application_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO application_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO application_user;

-- Revoke high-risk/privileged operations from application_user
REVOKE TRUNCATE, TRIGGER, REFERENCES ON ALL TABLES IN SCHEMA public FROM application_user;

-- 6. Grant ADMIN_USER permissions (DDL + DML)
GRANT ALL PRIVILEGES ON SCHEMA public TO admin_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO admin_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO admin_user;

-- 7. Document the setup
COMMENT ON ROLE readonly_user IS 'Read-only access for auditing and monitoring';
COMMENT ON ROLE reporting_user IS 'Access restricted to financial, sales, and reporting tables';
COMMENT ON ROLE application_user IS 'Operational read/write access for the main web application';
COMMENT ON ROLE admin_user IS 'Administrative access for schema migrations and upgrades';
