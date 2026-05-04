# Scope and boundaries

## Authorized scope

Testing is limited to:

- Local MCP gateway code owned by the operator
- Local lab systems owned by the operator
- Synthetic logs and synthetic test cases
- Explicitly authorized systems and repositories
- Defensive validation of permissions, logging, containment, and remediation

## Out of scope

This repository must not be used for:

- Unauthorized third-party systems
- Credential theft
- Phishing
- Persistence
- Evasion
- Exfiltration
- Destructive automation
- Malware deployment
- Real-world exploitation without explicit authorization

## Safety rule

All tests should be framed as validation of defensive controls, not operational abuse.
