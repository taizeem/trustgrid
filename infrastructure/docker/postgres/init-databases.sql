-- Identity Service
CREATE USER identity_user WITH PASSWORD 'identity_secure_pass_dev' CREATEDB;
CREATE DATABASE trustgrid_identity OWNER identity_user;
GRANT ALL PRIVILEGES ON DATABASE trustgrid_identity TO identity_user;

-- Vendor & Assessment Service
CREATE USER vendor_user WITH PASSWORD 'vendor_secure_pass_dev' CREATEDB;
CREATE DATABASE trustgrid_vendor OWNER vendor_user;
GRANT ALL PRIVILEGES ON DATABASE trustgrid_vendor TO vendor_user;

-- Workflow Service
CREATE USER workflow_user WITH PASSWORD 'workflow_secure_pass_dev' CREATEDB;
CREATE DATABASE trustgrid_workflow OWNER workflow_user;
GRANT ALL PRIVILEGES ON DATABASE trustgrid_workflow TO workflow_user;

-- Document Service
CREATE USER doc_user WITH PASSWORD 'doc_secure_pass_dev' CREATEDB;
CREATE DATABASE trustgrid_document OWNER doc_user;
GRANT ALL PRIVILEGES ON DATABASE trustgrid_document TO doc_user;

-- Risk Service
CREATE USER risk_user WITH PASSWORD 'risk_secure_pass_dev' CREATEDB;
CREATE DATABASE trustgrid_risk OWNER risk_user;
GRANT ALL PRIVILEGES ON DATABASE trustgrid_risk TO risk_user;

-- Integrations & Webhooks Service
CREATE USER integration_user WITH PASSWORD 'integration_secure_pass_dev' CREATEDB;
CREATE DATABASE trustgrid_integrations OWNER integration_user;
GRANT ALL PRIVILEGES ON DATABASE trustgrid_integrations TO integration_user;