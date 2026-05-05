# Danger

Danger is a defensive cybersecurity research repository for building and validating a local MCP gateway: a policy-controlled layer between an LLM, its tools, and an authorized lab environment.

The project goal is to make tool-using LLM workflows safer by enforcing permissions outside the model, logging every decision, and testing the gateway with synthetic adversarial prompts before real integrations are trusted.

## Doctrine

> Defensively motivated, offensively aware in testing, morally constrained by authorization, containment, and auditability.

## Current focus

- MCP tool-permission policy design
- Prompt-injection validation
- Unsafe file, network, and shell access prevention
- Audit-log schema design
- Detection logic for policy bypass attempts
- Synthetic red-team validation cases
- Remediation and validation reporting

## Repository layout

| Path | Purpose |
|---|---|
| `docs/scope-and-boundaries.md` | Project scope, authorization model, and operating constraints |
| `docs/threat-model.md` | Assets, trust boundaries, misuse cases, and controls |
| `docs/redteam-validation-plan.md` | Defensive validation plan for the gateway |
| `configs/mcp-permission-policy.yaml` | Initial deny-by-default MCP permission policy |
| `schemas/audit-log-schema.json` | Structured audit event schema |
| `tests/redteam-eval-cases.jsonl` | Synthetic test cases for safe validation |
| `scripts/validate_cases.py` | Lightweight validator for test-case formatting |
| `detections/sigma/mcp-policy-bypass-attempt.yml` | Experimental detection rule for suspicious gateway events |
| `reports/validation-report-template.md` | Report template for validation results |

## Working model

The LLM is treated as useful but not trusted. The gateway is responsible for enforcing policy before execution. Every allowed, denied, redacted, or review-required action should produce an audit event.

## Status

Foundation branch: `cyber-gateway-foundation`.
