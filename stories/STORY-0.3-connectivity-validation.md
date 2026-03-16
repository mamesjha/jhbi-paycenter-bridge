# STORY-0.3 – Validate Connectivity and Receive First Raw Event

| Field | Value |
|-------|-------|
| **Story ID** | STORY-0.3 |
| **Epic** | [EPIC-0 – PayCenter Infrastructure Discovery](../epics/EPIC-0-paycenter-infrastructure-discovery.md) |
| **Status** | 🔴 Blocked – Requires STORY-0.1 |
| **Points** | 5 |
| **Priority** | P0 – Critical Path |

## User Story

As a bridge service developer, I need to verify that I can successfully connect to the JH PayCenter event stream and receive at least one real (or sandbox) event per rail so that connectivity is confirmed before building the full consumer service.

## Background

Until the team has successfully connected to the PayCenter event stream and consumed a live message, all downstream development carries connectivity risk. This story de-risks that path by establishing a minimal proof-of-concept connection using the credentials and endpoints obtained in STORY-0.1.

## Acceptance Criteria

- [ ] A standalone Python proof-of-concept script can connect to the PayCenter event stream using credentials from GCP Secret Manager (or local `.env` during discovery)
- [ ] At least one raw event consumed per rail (Zelle, RTP, FedNow) — either from sandbox or production
- [ ] Raw consumed messages saved to `docs/schemas/paycenter/` as confirmed examples (feeds STORY-0.2 if not already completed)
- [ ] Connection latency and message throughput characteristics documented
- [ ] TLS certificate chain verified; any pinning requirements documented
- [ ] Proof-of-concept script committed to `scripts/poc_consumer.py` with setup instructions in its docstring
- [ ] Any firewall, VPN, or IP allowlisting requirements documented in `docs/paycenter-integration-notes.md`

## Proof-of-Concept Script Requirements

The script should:
- Accept broker URL, topic, group ID, and credential paths via environment variables or CLI args
- Print each consumed message as raw JSON to stdout
- Run for a configurable duration (default: 60 seconds) then exit cleanly
- **Not** be used in production; for discovery only

## Definition of Done

- [ ] POC script runs successfully in local dev environment against sandbox or production
- [ ] At least one message per rail captured and saved
- [ ] No hardcoded credentials in committed code
- [ ] Findings appended to `docs/paycenter-integration-notes.md`
