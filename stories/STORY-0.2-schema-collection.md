# STORY-0.2 – Collect and Document Raw Payload Schemas Per Rail

| Field | Value |
|-------|-------|
| **Story ID** | STORY-0.2 |
| **Epic** | [EPIC-0 – PayCenter Infrastructure Discovery](../epics/EPIC-0-paycenter-infrastructure-discovery.md) |
| **Status** | 🔴 Blocked – Requires STORY-0.1 |
| **Points** | 5 |
| **Priority** | P0 – Critical Path |

## User Story

As a bridge service developer, I need the exact raw payload schema for each payment rail (Zelle, RTP, FedNow) emitted by JH PayCenter so that I can implement accurate deserialization, validation, and field mapping logic.

## Background

The current schema examples in `docs/schemas/paycenter/` are **draft approximations** based on Early Warning Services (EWS) Zelle API documentation and ISO 20022 standards. They have not been validated against actual JH PayCenter output. This story replaces those drafts with confirmed, authoritative schemas.

Key unknowns:
- Whether PayCenter wraps rail-specific payloads in an envelope structure
- The exact field names and types for each rail (Zelle vs RTP vs FedNow differ significantly at the protocol level)
- How `paymentStatus`, `transactionId`, and rail type are surfaced in the raw payload
- Whether serialization format is JSON, Avro, Protobuf, or other

## Acceptance Criteria

- [ ] Raw Zelle event payload schema obtained from JH (or captured from sandbox) — at minimum one COMPLETED and one FAILED example
- [ ] Raw RTP event payload schema obtained from JH — at minimum one COMPLETED and one FAILED example
- [ ] Raw FedNow event payload schema obtained from JH — at minimum one COMPLETED and one FAILED example
- [ ] All example payloads committed to `docs/schemas/paycenter/` with per-rail subdirectories
- [ ] Serialization format confirmed (JSON, Avro, Protobuf)
- [ ] If Avro or Protobuf: schema registry endpoint documented and `.avsc` / `.proto` files committed to repo
- [ ] PII-bearing fields identified and documented in `docs/schemas/paycenter/README.md`
- [ ] Field mappings between each rail and the unified bridge output model documented

## Deliverables

```
docs/schemas/paycenter/
├── README.md               ← updated with confirmed field list and PII annotation
├── zelle/
│   ├── completed.json
│   ├── failed.json
│   └── returned.json
├── rtp/
│   ├── completed.json
│   └── failed.json
└── fednow/
    ├── completed.json
    └── failed.json
```

## Definition of Done

- [ ] All example payloads reviewed with JH integration team and confirmed as accurate
- [ ] README updated to reflect confirmed schemas (draft warning removed)
- [ ] STORY-0.4 (Pydantic data contract) can proceed based on these schemas
