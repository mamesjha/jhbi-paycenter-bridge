# JHA PayCenter Payment Events Bridge

> **Python · Kafka → GCP Pub/Sub · Cloud Run · Terraform**

A cloud-native bridge service that consumes raw real-time payment events from JH PayCenter and publishes them to a unified GCP Pub/Sub topic for downstream processing.

## Payment Rails Supported

| Rail | Network | Operator |
|------|---------|----------|
| **Zelle** | Zelle Network | Early Warning Services |
| **RTP** | Real-Time Payments | The Clearing House (TCH) |
| **FedNow** | FedNow Service | Federal Reserve |

## Architecture

```
JH PayCenter  →  Kafka (raw events)  →  Python Bridge (Cloud Run)  →  GCP Pub/Sub
```

## Repository Structure

```
epics/          # Epic-level descriptions and requirements
stories/        # Individual user stories per epic
docs/           # Design document, schemas, and integration notes
  schemas/
    paycenter/  # Draft PayCenter event schema examples (per rail)
```

## Epics

| Epic | Title | Status |
|------|-------|--------|
| [EPIC-0](epics/EPIC-0-paycenter-infrastructure-discovery.md) | PayCenter Infrastructure Discovery | 🔴 Blocked – Requires JH Engagement |
| [EPIC-1](epics/EPIC-1-kafka-consumer.md) | Kafka Consumer Service | 🔵 Backlog |
| [EPIC-2](epics/EPIC-2-pubsub-integration.md) | GCP Pub/Sub Integration | 🔵 Backlog |
| [EPIC-3](epics/EPIC-3-cloud-run-deployment.md) | Cloud Run Deployment | 🔵 Backlog |
| [EPIC-4](epics/EPIC-4-terraform-iac.md) | Terraform Infrastructure as Code | 🔵 Backlog |
| [EPIC-5](epics/EPIC-5-observability.md) | Observability & Operations | 🔵 Backlog |
| [EPIC-6](epics/EPIC-6-testing.md) | Testing & Quality Assurance | 🔵 Backlog |

## Tech Stack

- **Language:** Python 3.11
- **Kafka Client:** confluent-kafka-python
- **Pub/Sub Client:** google-cloud-pubsub
- **Health API:** FastAPI / Uvicorn
- **Metrics:** OpenTelemetry + GCP exporter
- **Runtime:** Google Cloud Run (min-instances = 1)
- **IaC:** Terraform >= 1.6
- **Secrets:** GCP Secret Manager

## Prerequisites

**EPIC-0 must be completed before EPIC-1 or EPIC-2 development begins.** The following must be resolved with the JH PayCenter integration team:

- Kafka broker hostname(s), port, and topic name(s) for raw PayCenter events
- Authentication mechanism (SASL or mTLS) and credential provisioning process
- Confirmation of raw event schema per rail type (Zelle, RTP, FedNow)
- Network connectivity path (public internet vs VPN/peering) from GCP to JH Kafka

See [Appendix A of the design document](docs/JHA_PayCenter_Bridge_Design_Document.docx) for the full list of integration questions.

---

*Design Document:* [docs/JHA_PayCenter_Bridge_Design_Document.docx](docs/JHA_PayCenter_Bridge_Design_Document.docx)
