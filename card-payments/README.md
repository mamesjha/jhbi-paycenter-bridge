# Card Payment CDC Hammer

Generates realistic credit/debit card payments with **Luhn-valid PANs** and hammers SQL Server CDC to measure its impact on a high-write OLTP workload.

> ⚠️ **TEST DATA ONLY.** PANs are fictitious but pass the Luhn check. Never run against a production database or store real PANs without encryption (PCI DSS Req 3.3).

---

## Files

| File | Description |
|------|-------------|
| `card_payments_schema.sql` | DDL for `dbo.card_transaction` plus reference tables and CDC enable commands |
| `card_cdc_hammer.py` | Generator + multi-threaded CDC load driver |
| `requirements.txt` | Python dependencies |

---

## Quick Start

### 1. Prerequisites

- SQL Server 2022 (or 2019) with SQL Server Agent running
- Python 3.9+
- [ODBC Driver 17 or 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

```bash
pip install -r requirements.txt
```

### 2. Create the database and table

Connect to your **non-production** SQL Server instance and run:

```sql
CREATE DATABASE CDC_BENCHMARK_DB;
GO
USE CDC_BENCHMARK_DB;
GO
```

Then execute `card_payments_schema.sql` in full. This creates:

- `dbo.card_network` — Visa / MC / Amex / Discover reference
- `dbo.merchant_category` — MCC reference (15 codes)
- `dbo.response_code` — ISO 8583 response codes
- `dbo.card_transaction` — the hot table (37 columns, 6 non-clustered indexes)

### 3. Run the baseline phase (no CDC)

```bash
python card_cdc_hammer.py \
    --server localhost \
    --database CDC_BENCHMARK_DB \
    --user sa \
    --password <your_password> \
    --duration 120 \
    --threads 8 \
    --tps 500 \
    --confirm
```

The script pauses after the baseline and prompts you to enable CDC before continuing to Phase 2.

### 4. Enable CDC (when prompted)

```sql
USE CDC_BENCHMARK_DB;
EXEC sys.sp_cdc_enable_db;
GO
EXEC sys.sp_cdc_enable_table
    @source_schema        = N'dbo',
    @source_name          = N'card_transaction',
    @role_name            = NULL,
    @supports_net_changes = 1;
GO
```

Press **Enter** in the terminal — Phase 2 begins.

### 5. Read the report

At the end you get a side-by-side delta table:

```
======================================================================
  DELTA: CDC vs Baseline
======================================================================
  actual_tps             baseline=498.3  cdc=312.1  delta=-186.2  (-37.4%)
  latency_p50_ms         baseline=12.1   cdc=18.4   delta=+6.3    (+52.1%)
  latency_p95_ms         baseline=28.7   cdc=61.2   delta=+32.5   (+113.2%)
  latency_p99_ms         baseline=45.1   cdc=89.6   delta=+44.5   (+98.7%)
  cpu_avg_pct            baseline=18.2%  cdc=27.4%  delta=+9.2    (+50.5%)
  log_growth_mb          baseline=124.1  cdc=198.3  delta=+74.2   (+59.8%)
======================================================================
```

Output files written to `--output-dir` (default: current directory):
- `card_cdc_hammer_<ts>.json` — full structured results
- `card_cdc_hammer_<ts>.csv` — one row per phase, easy to paste into Excel

---

## What the script generates

### Card data

| Field | Detail |
|-------|--------|
| PAN | Luhn-valid, correct BIN prefix per network |
| Networks | Visa (4xxx, 16d), Mastercard (51–55 / 2221–2720, 16d), Amex (34/37, 15d), Discover (6011/644–649/65, 16d) |
| Card types | 60% Credit · 30% Debit · 10% Prepaid |
| Entry modes | 40% Chip · 30% Contactless · 20% Ecommerce · 7% Swipe · 3% Manual |
| Response codes | 82% Approved (00) · 6% Do Not Honor (05) · 5% NSF (51) · … |

### DML mix (per worker thread)

| Operation | Share | Details |
|-----------|-------|---------|
| INSERT new transaction | 70% | Full card transaction |
| UPDATE → SETTLED | ~9% | Sets `txn_status='SETTLED'`, `settlement_timestamp` |
| UPDATE fraud flag | ~8% | Sets `is_fraud_flag=1`, random `fraud_score` 0.70–1.00 |
| INSERT VOID reversal | ~7% | New row linked via `original_txn_id` |

### CDC capture latency probe

After Phase 2, the script inserts 5 probe rows and polls `cdc.dbo_card_transaction_CT` until each appears, reporting mean and max capture lag in milliseconds.

---

## CLI reference

| Flag | Default | Description |
|------|---------|-------------|
| `--server` | `localhost` | SQL Server host/IP |
| `--database` | `CDC_BENCHMARK_DB` | Target database |
| `--user` | `sa` | SQL login |
| `--password` | *(required)* | SQL password |
| `--duration` | `60` | Seconds per phase |
| `--threads` | `8` | Concurrent worker threads |
| `--tps` | `300` | Target transactions per second (token bucket) |
| `--skip-cdc-phase` | off | Run baseline only, skip CDC phase |
| `--no-cleanup` | off | Leave rows in table after run |
| `--output-dir` | `.` | Where to write JSON/CSV results |
| `--confirm` | *(required)* | Safety gate — confirms non-production target |

---

## Tuning tips

- **Raise `--tps` until you saturate CDC** — the `sp_cdc_scan` job typically falls behind above ~200–300 TPS on default settings (5-second polling interval).
- **Increase CDC polling frequency** to stress the log reader more aggressively:
  ```sql
  EXEC sys.sp_cdc_change_job @job_type='capture', @pollinginterval=1;
  ```
- **Watch `log_growth_mb`** — native CDC holds the log open until the capture job drains; expect 40–80% more log growth vs. baseline.
- **Watch `latency_p99_ms`** — p99 latency typically inflates 2–4× at 300+ TPS with CDC enabled due to log contention.
