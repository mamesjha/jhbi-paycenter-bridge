# EPIC-2 – GCP Pub/Sub Integration

| Field | Value |
|-------|-------|
| **Epic ID** | EPIC-2 |
| **Status** | 🔵 Backlog |
| **Priority** | P0 – Critical Path |
| **Depends On** | EPIC-1 (Kafka Consumer Service, including PII tokenization) |
| **Estimate** | 1 sprint |

## Summary

Configure GCP Pub/Sub resources and implement the publishing logic, including message attributes for downstream filtering, ordering keys, and dead letter handling. All messages published to Pub/Sub contain tokenized PII — no plain-text personal data.

## Goal

Publish all valid Zelle, RTP, and FedNow raw payment events — with PII fields tokenized — to a single unified GCP Pub/Sub topic (`payment-events`) with rich message attributes, enabling downstream subscribers to filter and route without deserializing the full payload.

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-2.1 | The service SHALL publish each valid, PII-tokenized payment event to the `payment-events` Pub/Sub topic with the sanitized JSON payload as the message body |
| FR-2.2 | The service SHALL attach message attributes: `rail_type`, `payment_status`, `institution_id`, `event_id`, `source_topic`, `kafka_offset` |
| FR-2.3 | A separate Pub/Sub topic `payment-events-dead-letter` SHALL receive messages that cannot be parsed or published |
| FR-2.4 | The dead letter message SHALL include: original raw Kafka bytes, topic/partition/offset, error type, error message, and timestamp. **Note:** dead letter messages contain the raw pre-tokenization payload and must be access-controlled accordingly |
| FR-2.5 | Pub/Sub message ordering keys SHALL be set to `transactionId` where available |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-2.1 | The publisher SHALL use batch settings: `max_messages=100`, `max_latency=0.1s` |
| NFR-2.2 | The service SHALL retry Pub/Sub publish failures up to 5 times with exponential backoff before routing to dead letter |
| NFR-2.3 | Published messages SHALL log the Pub/Sub message ID alongside the Kafka offset for end-to-end traceability |

## Message Attributes

| Attribute | Example | Source |
|-----------|---------|--------|
| `rail_type` | `ZELLE` | Rail type field in raw PayCenter event (field name TBD — see EPIC-0) |
| `payment_status` | `COMPLETED` | Payment status field in raw PayCenter event |
| `institution_id` | `FI-00123` | Institution ID field in raw PayCenter event |
| `event_id` | `uuid` | Event/transaction ID field in raw PayCenter event |
| `source_topic` | `paycenter-zelle-events` | Kafka topic name (confirmed in EPIC-0, set by bridge) |
| `kafka_offset` | `1048293` | Kafka partition offset (set by bridge) |

## Published Payload — PII Field Handling

The following fields are present in the published Pub/Sub message body but contain **tokens, not original values**. Tokenization is performed upstream in EPIC-1 (STORY-1.7) before this stage is reached.

| Field | Published Value |
|-------|----------------|
| `sender.tokenValue` | Opaque token (e.g. `TKN-a3f9...`) |
| `sender.displayName` | Opaque token (e.g. `TKN-b12c...`) |
| `receiver.tokenValue` | Opaque token (e.g. `TKN-c77d...`) |
| `receiver.displayName` | Opaque token (e.g. `TKN-d44e...`) |
| `memo` | Opaque token (e.g. `TKN-e91f...`) |

> ⚠️ Exact field paths will be confirmed once PayCenter raw schemas are obtained in EPIC-0.

## Dead Letter Topic — Access Control Note

The `payment-events-dead-letter` topic preserves the **original raw Kafka bytes**, which may contain un-tokenized PII. Access to this topic must be restricted to authorized ops/engineering roles only. Downstream applications must not be granted subscriber access to the dead letter topic.

## Acceptance Criteria

- [ ] `payment-events` Pub/Sub topic receives messages with correct attributes for all three rail types
- [ ] A downstream test subscriber filtering on `rail_type = ZELLE` receives only Zelle events
- [ ] Published message bodies contain tokenized values for all PII fields — verified by inspecting a pulled message
- [ ] A simulated publish failure routes the message to `payment-events-dead-letter` after retries are exhausted
- [ ] Dead letter topic is access-controlled — subscriber access denied for non-ops service accounts
- [ ] Pub/Sub message IDs are logged alongside Kafka offsets

## Stories

| Story | Title |
|-------|-------|
| [STORY-2.1](../stories/STORY-2.1-pubsub-publisher.md) | Pub/Sub publisher client setup and batch config |
| [STORY-2.2](../stories/STORY-2.2-message-attributes.md) | Message attribute mapping from PayCenter event |
| [STORY-2.3](../stories/STORY-2.3-ordering-keys.md) | Ordering key configuration by transactionId |
| [STORY-2.4](../stories/STORY-2.4-dead-letter-publisher.md) | Dead letter topic publishing and access control |
| [STORY-2.5](../stories/STORY-2.5-publish-retry.md) | Publish retry logic with exponential backoff |
