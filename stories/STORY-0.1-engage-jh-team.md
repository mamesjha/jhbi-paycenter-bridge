# STORY-0.1 – Engage JH PayCenter Team and Document Raw Event Mechanism

| Field | Value |
|-------|-------|
| **Story ID** | STORY-0.1 |
| **Epic** | [EPIC-0 – PayCenter Infrastructure Discovery](../epics/EPIC-0-paycenter-infrastructure-discovery.md) |
| **Status** | 🔴 Blocked – Requires JH PayCenter engagement |
| **Points** | 3 |
| **Priority** | P0 – Critical Path |

## User Story

As a bridge service developer, I need to understand how JH PayCenter exposes raw payment events for Zelle, RTP, and FedNow so that I can design the correct consumer integration.

## Background

Jack Henry PayCenter is a faster payments hub supporting Zelle, RTP, and FedNow rails. Before any consumer code can be written, the team must confirm the exact mechanism by which PayCenter surfaces these events externally. Options may include a managed Kafka cluster, a proprietary event bus, webhooks, or a polling API — but none of this has been confirmed.

This story covers the discovery and documentation phase with the JH integration team.

## Acceptance Criteria

- [ ] Kickoff meeting held with JH PayCenter integration team; meeting notes documented
- [ ] Confirmed whether PayCenter uses Kafka, a proprietary event bus, or another mechanism for external event delivery
- [ ] Confirmed which Kafka topics (or equivalent) correspond to Zelle, RTP, and FedNow events respectively
- [ ] Confirmed authentication mechanism (SASL/SSL, mTLS, API key, OAuth, etc.)
- [ ] Confirmed whether a consumer group model is supported and how offset management works
- [ ] Confirmed whether a sandbox/non-prod environment is available for integration testing
- [ ] All findings documented in `docs/paycenter-integration-notes.md` in the repo

## Open Questions to Resolve (see also Appendix A of design doc)

| # | Question |
|---|----------|
| Q1 | Does PayCenter use Apache Kafka for event delivery, or a different mechanism? |
| Q2 | If Kafka, what is the cluster endpoint and authentication method? |
| Q3 | Is a separate topic provided per rail type (Zelle, RTP, FedNow), or is it a unified topic with type differentiation in the payload? |
| Q4 | What consumer group naming conventions are required or recommended? |
| Q5 | Is there a non-production / sandbox environment available for initial testing? |
| Q6 | Who is the JH PayCenter integration team point of contact? What is the SLA for integration support? |

## Definition of Done

- [ ] Discovery notes are committed to the repo
- [ ] Integration contact established and recorded
- [ ] STORY-0.2 (schema collection) can proceed based on findings
