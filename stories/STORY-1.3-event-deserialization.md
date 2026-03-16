# STORY-1.3 – PayCenter Event Deserialization and Schema Validation

**Epic:** [EPIC-1 – Kafka Consumer Service](../epics/EPIC-1-kafka-consumer.md)
**Status:** 🔴 Blocked – Requires EPIC-0 (STORY-0.4) | **Points:** 5

## User Story

> As a platform engineer, I want each consumed Kafka message to be deserialized and validated against the confirmed PayCenter event schema so that only well-formed, complete payment events are forwarded to Pub/Sub.

## Details

- Deserialize message value as UTF-8 JSON (or Avro/Protobuf if confirmed in EPIC-0)
- Validate required fields using the `PayCenterEvent` Pydantic v2 model defined in STORY-0.4
- Schema model lives in `src/models/paycenter.py` (see STORY-0.4 for model definition)
- If Schema Registry is in use (TBD from EPIC-0 discovery), add Avro/JSON Schema deserialization
- Required fields and their exact names are **TBD pending EPIC-0 completion** — do not begin this story until STORY-0.4 is done

> ⚠️ **Do not hard-code field names** (e.g. `eventId`, `pmtRailType`) until the confirmed PayCenter schema is available from EPIC-0. The Pydantic model in `src/models/paycenter.py` is the authoritative source.

## Acceptance Criteria

- [ ] Valid raw PayCenter JSON is parsed into a typed `PayCenterEvent` Pydantic model
- [ ] Missing required fields raise a `ValidationError` and route to dead letter
- [ ] Unknown extra fields are ignored (non-strict mode)
- [ ] Invalid JSON (not parseable) is caught and routed to dead letter with raw bytes preserved
- [ ] Unit tests cover: valid payload, missing required field, invalid JSON, extra fields
- [ ] Test fixtures use confirmed payload examples from `docs/schemas/paycenter/` (populated in STORY-0.2)

## Notes

- **Blocked on EPIC-0**: Field names, types, and schema structure are unknown until PayCenter infrastructure discovery is complete
- Schema Registry integration to be determined after JH response (Appendix A Q8)
- Rail type differentiation approach (separate topics vs. payload field) confirmed in STORY-0.1
