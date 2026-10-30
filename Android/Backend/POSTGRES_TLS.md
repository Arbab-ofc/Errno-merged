# PostgreSQL TLS configuration

The backend forces `sslmode=verify-full` and supplies a trusted CA file for
PostgreSQL URLs. The default is the public Supabase root certificate at
`certs/supabase-prod-ca-2021.crt`; set `PGSSLROOTCERT` or
`ERRNO_PGSSLROOTCERT` to override it for another managed PostgreSQL endpoint.

If the URL, trusted CA, certificate chain, or hostname cannot be verified, the
backend fails closed. It does not fall back to SQLite for a PostgreSQL URL.
Local SQLite remains available when no PostgreSQL URL is configured.
