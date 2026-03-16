# Event 800 Schema Examples

This folder contains example JSON payloads for Event 800 (Payment Hub Activity Notifications) per rail type and payment status.

> ⚠️ **These are draft examples** based on the Early Warning Services (EWS) Zelle API and ISO 20022 messaging standards. Field names, enums, and structure **must be validated** against the official JH PayCenter EES documentation once access is provisioned. See [Appendix A](../../docs/JHA_PayCenter_Bridge_Design_Document.docx) for the list of open questions for the JH integration team.

## Zelle Schemas

| File | Status | Description |
|------|--------|-------------|
| [`zelle_completed.json`](zelle_completed.json) | `COMPLETED` | Successful P2P send, settled by EWS |
| [`zelle_failed.json`](zelle_failed.json) | `FAILED` | Rejected by EWS – closed account (`AC04`) |
| [`zelle_returned.json`](zelle_returned.json) | `RETURNED` | Return of a prior transaction – wrong amount (`AM09`) |

## RTP Schemas

*Pending JH integration team response — see Appendix A Q1–Q5*

## FedNow Schemas

*Pending JH integration team response — see Appendix A Q1–Q5*

## Key Zelle-Specific Fields

| Field | Description |
|-------|-------------|
| `zelleTransactionId` | Zelle network transaction ID (ZL- prefix) |
| `ewsTransactionId` | Early Warning Services internal transaction ID |
| `tokenType` | How the receiver was addressed: `EMAIL` or `PHONE` |
| `tokenValue` | Masked alias (phone or email) — never the raw account number |
| `fraudIndicators.riskScore` | EWS Financial Crimes Defender risk score (0–100) |
| `fraudIndicators.riskBand` | Risk band: `LOW`, `MEDIUM`, `HIGH` |
| `fraudIndicators.fdcFlags` | Array of Financial Crimes Defender flag codes, if any |
| `returnReasonCode` | ISO 20022 reason code on `FAILED` or `RETURNED` events |

## Common Return Reason Codes

| Code | Meaning |
|------|---------|
| `AC04` | Closed account number |
| `AC06` | Blocked account |
| `AM09` | Wrong amount |
| `DUPL` | Duplicate payment |
| `FRAD` | Fraudulent origin |
| `NOAS` | No answer from customer |
| `RUTA` | Incorrect routing |
