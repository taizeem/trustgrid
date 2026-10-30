#!/bin/bash
set -e

# Function to create user and database safely
create_service_db() {
    local db=$1
    local user=$2
    local password=$3
    echo "Creating user '$user' and database '$db'..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$user') THEN
                CREATE ROLE $user WITH LOGIN PASSWORD '$password';
            END IF;
        END
        \$\$;
        SELECT 'CREATE DATABASE $db WITH OWNER $user'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
        GRANT ALL PRIVILEGES ON DATABASE $db TO $user;
EOSQL
}

create_service_db "$IDENTITY_DB_NAME" "$IDENTITY_DB_USER" "$IDENTITY_DB_PASSWORD"
create_service_db "$VENDOR_DB_NAME" "$VENDOR_DB_USER" "$VENDOR_DB_PASSWORD"
create_service_db "$WORKFLOW_DB_NAME" "$WORKFLOW_DB_USER" "$WORKFLOW_DB_PASSWORD"
create_service_db "${DOC_DB_NAME:-trustgrid_document}" "${DOC_DB_USER:-doc_user}" "${DOC_DB_PASSWORD:-doc_secure_pass_dev}"
create_service_db "$RISK_DB_NAME" "$RISK_DB_USER" "$RISK_DB_PASSWORD"
create_service_db "${INTEGRATIONS_DB_NAME:-trustgrid_integrations}" "${INTEGRATIONS_DB_USER:-integration_user}" "${INTEGRATIONS_DB_PASSWORD:-integration_secure_pass_dev}"

echo "All service databases initialized successfully."