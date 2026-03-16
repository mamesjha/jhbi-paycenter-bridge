# Real-Time Payment Samples

Schema-complete synthetic payment message samples and a Faker-based generator for **FedNow**, **RTP (The Clearing House)**, and **Zelle (EWS)**.

## Contents

```
payment_samples/
├── generate_payments.py      # Faker-based generator (all 14 message types)
├── payment_samples.py        # All samples as importable Python constants
├── fednow/                   # FedNow ISO 20022 samples
│   ├── pacs008_credit_transfer.json
│   ├── pacs002_payment_status.json
│   ├── pacs004_return.json
│   ├── pain013_request_for_payment.json
│   ├── pain014_rfp_response.json
│   └── lmt_liquidity_transfer.json
├── rtp/                      # RTP ISO 20022 samples
│   ├── pacs008_credit_transfer.json
│   ├── pacs002_payment_status.json
│   ├── pacs004_return.json
│   ├── pain013_request_for_payment.json
│   └── pain014_rfp_response.json
├── zelle/                    # Zelle REST/JSON samples
│   ├── send_payment.json
│   ├── payment_status.json
│   └── return_reversal.json
└── generated_payments/       # 14,000 synthetic records (1k per message type)
    ├── fednow_*.jsonl
    ├── rtp_*.jsonl
    └── zelle_*.jsonl
```

## Message Types

| Network | Message Type | ISO Type | Notes |
|---------|-------------|----------|-------|
| FedNow | Credit Transfer | pacs.008.001.08 | $500K limit, 20s window |
| FedNow | Payment Status | pacs.002.001.10 | ACCP / RJCT |
| FedNow | Return | pacs.004.001.09 | CUST, DUPL, FRAD reason codes |
| FedNow | Request for Payment | pain.013.001.07 | Invoice line items |
| FedNow | RfP Response | pain.014.001.07 | ACCP / RJCT |
| FedNow | Liquidity Transfer | pacs.009 | TOP_UP / DRAWDOWN via Fedwire |
| RTP | Credit Transfer | pacs.008.001.07 | $1M limit, 15s window |
| RTP | Payment Status | pacs.002.001.10 | ACTC → ACWP → ACCP lifecycle |
| RTP | Return | pacs.004.001.08 | |
| RTP | Request for Payment | pain.013.001.06 | |
| RTP | RfP Response | pain.014.001.06 | |
| Zelle | Send Payment | REST/JSON | EWS token-based, EMAL/PHON |
| Zelle | Payment Status | REST/JSON | COMPLETED / REJECTED / PENDING |
| Zelle | Cancellation | REST/JSON | PENDING only; Reg E dispute path |

## Usage

### Generate synthetic data

```bash
pip install faker

# Generate 1,000 records of every message type in JSONL format
python generate_payments.py --count 1000 --output-dir generated_payments --format jsonl --seed 2025

# Generate a specific network/type as JSON array
python generate_payments.py --network fednow --type credit_transfer --count 500 --format json

# Available networks: fednow, rtp, zelle
# Available types:    credit_transfer, payment_status, return, rfp, rfp_response, liquidity (fednow only), cancellation (zelle only)
```

### Use as Python constants

```python
from payment_samples import get_sample, ALL_SAMPLES

ct = get_sample("fednow", "pacs008_credit_transfer")
print(ct["iso20022"]["FIToFICstmrCdtTrf"]["CdtTrfTxInf"]["IntrBkSttlmAmt"])
```

## Realism Details

- **15%** FedNow payment rejections (realistic RJCT rate)
- **12%** RTP payment rejections
- **80%** Zelle recipients enrolled; 20% trigger PENDING not-enrolled flow
- **20%** Zelle RfP responses are declines
- **85%** Zelle cancellation requests succeed (PENDING only)
- Real US bank ABA routing numbers and BICs
- UETRs are RFC 4122 v4 UUIDs
- Timestamps are consistent across related messages (status references parent CT)

## Generated Data

The `generated_payments/` directory contains pre-generated JSONL files (1,000 records each, seed 2025):

```
fednow_credit_transfer.jsonl    1,000 records
fednow_payment_status.jsonl     1,000 records
fednow_return.jsonl             1,000 records
fednow_rfp.jsonl                1,000 records
fednow_rfp_response.jsonl       1,000 records
fednow_liquidity.jsonl          1,000 records
rtp_credit_transfer.jsonl       1,000 records
rtp_payment_status.jsonl        1,000 records
rtp_return.jsonl                1,000 records
rtp_rfp.jsonl                   1,000 records
rtp_rfp_response.jsonl          1,000 records
zelle_send_payment.jsonl        1,000 records
zelle_payment_status.jsonl      1,000 records
zelle_cancellation.jsonl        1,000 records
                               ----------
Total                          14,000 records
```

## Notes

- FedNow and RTP samples include both ISO 20022 canonical JSON (with `@Ccy`, `#text` binding conventions) and a flattened human-readable version side-by-side.
- Zelle samples are modeled on the Early Warning Services (EWS) private API; field names are realistic approximations.
- This data is for testing and development only. Do not use in production systems.
