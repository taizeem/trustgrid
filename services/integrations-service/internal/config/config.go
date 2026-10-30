package config

import (
	"fmt"
	"os"
)

type Config struct {
	Port                  string
	DBHost                string
	DBPort                string
	DBName                string
	DBUser                string
	DBPassword            string
	JWTSecretKey          string
	AllowInternalWebhooks bool
}

func Load() *Config {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8006"
	}

	dbHost := os.Getenv("INTEGRATIONS_DB_HOST")
	if dbHost == "" {
		dbHost = "postgres"
	}

	dbPort := os.Getenv("INTEGRATIONS_DB_PORT")
	if dbPort == "" {
		dbPort = "5432"
	}

	dbName := os.Getenv("INTEGRATIONS_DB_NAME")
	if dbName == "" {
		dbName = "trustgrid_integrations"
	}

	dbUser := os.Getenv("INTEGRATIONS_DB_USER")
	if dbUser == "" {
		dbUser = "integration_user"
	}

	dbPassword := os.Getenv("INTEGRATIONS_DB_PASSWORD")
	if dbPassword == "" {
		dbPassword = "integration_secure_pass_dev"
	}

	jwtSecret := os.Getenv("JWT_SECRET_KEY")
	if jwtSecret == "" {
		jwtSecret = "dev_insecure_jwt_secret_key_minimum_32_bytes_long_123"
	}

	allowInternal := os.Getenv("ALLOW_INTERNAL_WEBHOOKS") == "true"

	return &Config{
		Port:                  port,
		DBHost:                dbHost,
		DBPort:                dbPort,
		DBName:                dbName,
		DBUser:                dbUser,
		DBPassword:            dbPassword,
		JWTSecretKey:          jwtSecret,
		AllowInternalWebhooks: allowInternal,
	}
}

func (c *Config) DSN() string {
	return fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		c.DBHost, c.DBPort, c.DBUser, c.DBPassword, c.DBName,
	)
}
