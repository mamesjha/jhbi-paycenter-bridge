# STORY-1.7 – PII Tokenization Pipeline Step

**Epic:** [EPIC-1 – Kafka Consumer Service](../epics/EPIC-1-kafka-consumer.md)
**Status:** 🔵 Backlog | **Points:** 8

## User Story

> As a platform engineer, I want PII fields tokenized in-flight before any event is published to Pub/Sub so that downstream consumers never have access to plain-text personal data, and the bridge acts as the single point of PII control.

## Background

The JH PayCenter EES Event 800 payload includes the following PII fields that must be tokenized before the message is forwarded:

| Field Path | PII Type |
|------------|----------|
| `sender.tokenValue` | Phone number or email address |
| `sender.displayName` | Person's full name |
| `receiver.tokenValue` | Phone number or email address |
| `receiver.displayName` | Person's full name |
| `memo` | Free-text — may contain names, account numbers, or other sensitive content |

## Tokenization Requirements

- **Deterministic:** the same input value always produces the same token, enabling downstream correlation (e.g. linking multiple payments from the same sender without exposing the email address)
- **Non-reversible by downstream consumers:** tokens cannot be reversed without access to the token vault
- **Reversible by authorized systems:** ops tooling and fraud systems with vault access can resolve tokens back to PII for investigation
- **Consistent across rail types:** the same phone number appearing in a Zelle event and an RTP event maps to the same token

## Tokenization Approach (TBD)

The specific tokenization library or service is to be decided. Candidate options:

| Option | Notes |
|--------|-------|
| **Google Cloud DLP** — tokenization via `deidentifyContent` | Managed, audit-logged, supports format-preserving encryption. Higher latency (~100–200ms). |
| **Custom token vault** (e.g. HashiCorp Vault Transit) | Low latency, deterministic. Requires additional infrastructure. |
| **Format-Preserving Encryption (FPE)** via `pyffx` or `ff3-py` | Local, fast, deterministic. Key management required. |
| **HMAC-SHA256 with a secret key** | Simplest. Deterministic. One-way (not reversible). Suitable if reversal is not required. |

**Decision to be made before this story is started.** Add to open questions for architecture review.

## Details

- Tokenization is a pipeline step between `rail_filter` and `pubsub_publish` in the processing chain
- Implemented in `src/tokenizer.py` with a `TokenizerClient` interface so the backing implementation can be swapped
- Tokenization failures (vault unavailable, key error) route the message to the dead letter topic with `error_type = TOKENIZATION_FAILURE`
- The raw pre-tokenization payload is never logged, stored, or forwarded anywhere other than the dead letter topic
- Token values in logs appear as `[TOKENIZED]` placeholders

## Acceptance Criteria

- [ ] All five PII field paths are tokenized before Pub/Sub publish
- [ ] The same input value produces the same token on repeated runs (deterministic)
- [ ] A tokenization failure routes the message to the dead letter topic with `error_type = TOKENIZATION_FAILURE`
- [ ] No plain-text PII appears in any log output, metric label, or error message
- [ ] Unit tests cover: successful tokenization of all five fields, tokenization failure routing, determinism assertion (same input → same token)
- [ ] `TokenizerClient` is injectable (interface-based) so tests can run without a live vault

## Notes

- Blocked on tokenization approach decision (architecture review required)
- Dead letter messages contain pre-tokenization raw bytes — ensure DLT IAM is restricted (see EPIC-2, STORY-2.4)
