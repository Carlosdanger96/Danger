# Threat model

## System under test

A local MCP gateway that mediates requests between an LLM, available tools, local files, logs, APIs, and operator-approved lab systems.

## Core assumption

The model can be wrong, manipulated, or overconfident. The gateway must enforce safety and authorization independently of the model's response.

## Assets

| Asset | Why it matters |
|---|---|
| Tool permissions | Over-broad permissions can turn a benign assistant into an unsafe executor |
| Local files | File access must be scoped to approved project and lab paths |
| Network access | Egress must be explicit, logged, and limited to approved targets |
| Audit logs | Logs provide accountability, debugging evidence, and policy validation data |
| Secrets | Tokens, keys, credentials, and private data must not be exposed or logged unsafely |
| Agent chains | Delegation can blur responsibility and bypass intended controls |
| Policy configuration | Policy drift can silently expand risk |

## Trust boundaries

1. User prompt to LLM
2. LLM output to gateway
3. Gateway policy engine to tool call
4. Tool result back to gateway
5. Gateway output back to LLM or user
6. Gateway event to audit log
7. Local lab environment to external network

## Misuse cases and controls

| Misuse case | Control |
|---|---|
| Prompt injection asks the model to ignore rules | Gateway policy check before every tool call |
| Request attempts file traversal | Normalize paths and enforce allowed roots |
| Request attempts secret discovery | Block secret-like paths and redact secret-like outputs |
| Request attempts unauthorized network access | Domain allowlist and egress logging |
| Request attempts shell execution | Deny shell by default; require explicit command allowlist |
| Request asks to skip logging | Mandatory append-only audit event creation |
| Request chains agents to bypass policy | Limit chain depth and require explicit delegation scope |
| Policy grants too much access | Least-privilege review and test coverage |

## Control objective

The gateway should fail closed. When uncertain, it should deny or require review, preserve useful context, log the decision, and provide a remediation hint.
