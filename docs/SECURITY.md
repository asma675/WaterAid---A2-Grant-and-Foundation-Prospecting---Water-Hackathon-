# Security and privacy

## Defaults

- `ALLOW_INTERNAL_DATA_TO_EXTERNAL_AI=false`
- `LIVE_FETCH_ENABLED=false`
- External provider keys are server-side environment variables only.
- The frontend never receives provider secrets.

## Donor-data rule

Donor, board, relationship, CRM, private contact, and internal-note fields are not intended for external model calls. `scrub_external_payload` provides defense-in-depth redaction for obvious fields and email/phone patterns, but the primary control is architectural separation: do not send internal objects to external AI in the first place.

## Web fetching

The optional fetch utility blocks loopback/private/reserved network targets, checks `robots.txt`, refuses to proceed when robots policy cannot be verified, disables redirects, limits payload size, and is off by default. For production, prefer source-specific APIs and an outbound egress allowlist.

## Authentication

Authentication is intentionally not faked in this hackathon build. Production deployment should use the client's SSO/OIDC provider and role-based authorization before any private data is connected.
