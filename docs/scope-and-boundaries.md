# Scope and boundaries

This repository is for building and validating a local defensive cyber gateway: a policy-controlled layer between an LLM, its tools, and the operator's lab environment.

The working doctrine is:

> Defensively motivated, offensively aware in testing, morally constrained by authorization, containment, and auditability.

## Authorized working scope

Work in this repository should stay inside environments that are owned by the operator or explicitly authorized for testing. The first target environment is a local MCP gateway and its supporting files, logs, tools, and synthetic validation cases.

Allowed work includes:

- Designing MCP tool-permission policies
- Testing prompt-injection resistance with synthetic prompts
- Validating file, network, and shell access boundaries
- Building audit-log schemas and tamper-evidence checks
- Creating detection logic for policy bypass attempts
- Writing remediation plans and validation reports
- Using synthetic data instead of real secrets or third-party data

## Operating constraints

The gateway should assume the model can be manipulated. Safety cannot depend on the model choosing to behave correctly. Every tool call should be checked by policy before execution, every decision should be logged, and every permission should be narrow enough to explain and review.

The project should not contain live exploit chains, credential theft workflows, persistence mechanisms, stealth/evasion logic, destructive automation, or instructions for acting against systems without authorization. When adversarial cases are needed, they should be synthetic and used to test whether the gateway denies, contains, logs, or redirects the request.

## Design standard

A successful control is not just a refusal. A successful control should:

1. identify the risky request,
2. prevent unsafe execution,
3. preserve useful defensive context,
4. write an audit event, and
5. point to a concrete remediation step.
