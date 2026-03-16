"""
card_cdc_hammer.py
==================
Realistic credit/debit card payment generator that hammers SQL Server CDC.

Generates Luhn-valid PANs across Visa, Mastercard, Amex, and Discover,
then drives a configurable mix of INSERT / UPDATE / DELETE against
dbo.card_transaction while measuring:

  - Transaction throughput (TPS)
  - Latency percentiles (p50 / p95 / p99 / max)
  - CDC capture lag (time from INSERT commit to row visible in _CT table)
  - Log growth and truncation blocking
  - CPU and I/O via DMVs

Usage
-----
python card_cdc_hammer.py \\
    --server localhost \\
    --database CDC_BENCHMARK_DB \\
    --user sa --password <pw> \\
    --duration 120 \\
    --threads 8 \\
    --tps 500 \\
    --confirm

NOTE: TEST DATA ONLY — PANs are Luhn-valid but fictitious.
      Never run against a production database.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import queue
import random
import statistics
import string
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

try:
    import pyodbc
except ImportError:
    sys.exit("pip install pyodbc")

try:
    import psutil
except ImportError:
    sys.exit("pip install psutil")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CARD_NETWORKS = {
    "VISA":  {"prefix_ranges": [("4",)],
              "length": 16, "id": 1},
    "MC":    {"prefix_ranges": [("51","55"), ("2221","2720")],
              "length": 16, "id": 2},
    "AMEX":  {"prefix_ranges": [("34",), ("37",)],
              "length": 15, "id": 3},
    "DISC":  {"prefix_ranges": [("6011",), ("644","649"), ("65",)],
              "length": 16, "id": 4},
}

CARD_TYPES      = ["CREDIT"] * 6 + ["DEBIT"] * 3 + ["PREPAID"]
ENTRY_MODES     = ["CHIP"] * 40 + ["CONTACTLESS"] * 30 + ["ECOMMERCE"] * 20 + \
                  ["SWIPE"] * 7 + ["MANUAL"] * 3
CURRENCIES      = ["USD"] * 92 + ["EUR"] * 4 + ["GBP"] * 2 + ["CAD"] * 2
EXCHANGE_RATES  = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.73}

MERCHANT_DATA = [
    ("M000001", "Whole Foods Market",       "Austin",      "TX", 5411, "100001"),
    ("M000002", "CVS Pharmacy",             "Boston",      "MA", 5912, "100002"),
    ("M000003", "Shell Station",            "Chicago",     "IL", 5541, "100003"),
    ("M000004", "Chipotle Mexican Grill",   "Denver",      "CO", 5812, "100004"),
    ("M000005", "Amazon.com",               "Seattle",     "WA", 4816, "100005"),
    ("M000006", "Marriott Hotels",          "Atlanta",     "GA", 7011, "100006"),
    ("M000007", "Best Buy",                 "Minneapolis", "MN", 5732, "100007"),
    ("M000008", "Uber Technologies",        "San Fran",    "CA", 4121, "100008"),
    ("M000009", "Target",                   "Minneapolis", "MN", 5310, "100009"),
    ("M000010", "Home Depot",               "Atlanta",     "GA", 5999, "100010"),
    ("M000011", "Starbucks",                "Seattle",     "WA", 5812, "100011"),
    ("M000012", "Walmart",                  "Bentonville", "AR", 5310, "100012"),
    ("M000013", "Delta Air Lines",          "Atlanta",     "GA", 4111, "100013"),
    ("M000014", "Netflix",                  "Los Gatos",   "CA", 4816, "100014"),
    ("M000015", "Apple Store",              "Cupertino",   "CA", 5045, "100015"),
]

FIRST_NAMES = ["James","Mary","John","Patricia","Robert","Jennifer","Michael","Linda",
               "William","Barbara","David","Susan","Richard","Jessica","Joseph","Sarah"]
LAST_NAMES  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
               "Wilson","Moore","Taylor","Anderson","Jackson","White","Harris","Martin"]

RESPONSE_WEIGHTS = {
    "00": 82,   # Approved
    "05": 6,    # Do Not Honor
    "51": 5,    # Insufficient Funds
    "14": 2,    # Invalid Card Number
    "54": 2,    # Expired Card
    "91": 1,    # Issuer Unavailable
    "61": 1,    # Exceeds Limit
    "96": 1,    # System Error
}

APPROVED_CODES  = {"00"}
DECLINED_CODES  = set(RESPONSE_WEIGHTS.keys()) - APPROVED_CODES


# ---------------------------------------------------------------------------
# Luhn helpers
# ---------------------------------------------------------------------------

def _luhn_checksum(digits: str) -> int:
    total = 0
    reverse = digits[::-1]
    for i, d in enumerate(reverse):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10


def _luhn_complete(partial: str) -> str:
    """Append the Luhn check digit to a partial PAN string."""
    check = (10 - _luhn_checksum(partial + "0")) % 10
    return partial + str(check)


def generate_pan(network: str) -> str:
    """Return a Luhn-valid PAN for the given network."""
    cfg = CARD_NETWORKS[network]
    length = cfg["length"]

    # Pick a prefix range
    ranges = cfg["prefix_ranges"]
    chosen = random.choice(ranges)
    if len(chosen) == 1:
        prefix = chosen[0]
    else:
        lo, hi = int(chosen[0]), int(chosen[1])
        prefix = str(random.randint(lo, hi))

    # Fill middle digits randomly (leave room for check digit)
    fill_len = length - len(prefix) - 1
    middle = "".join(str(random.randint(0, 9)) for _ in range(fill_len))
    partial = prefix + middle
    return _luhn_complete(partial)


def mask_pan(pan: str) -> str:
    """Return first-6 *** last-4 masked PAN."""
    return pan[:6] + "*" * (len(pan) - 10) + pan[-4:]


def generate_token() -> str:
    """Simulate a network token (DPAN) — 16-char hex-like string."""
    return uuid.uuid4().hex[:16].upper()


# ---------------------------------------------------------------------------
# Payment record builder
# ---------------------------------------------------------------------------

def _rrn() -> str:
    return "".join(random.choices(string.digits, k=12))

def _stan() -> str:
    return "".join(random.choices(string.digits, k=6))

def _auth_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def _weighted_choice(weights: dict) -> str:
    keys   = list(weights.keys())
    wvals  = list(weights.values())
    return random.choices(keys, weights=wvals, k=1)[0]


def build_card_transaction(rng: random.Random | None = None) -> dict:
    """Build a single realistic card transaction dict."""
    r = rng or random

    network   = r.choice(list(CARD_NETWORKS.keys()))
    pan       = generate_pan(network)
    card_type = r.choice(CARD_TYPES)
    entry     = r.choice(ENTRY_MODES)

    now       = datetime.now(timezone.utc)
    exp_month = r.randint(1, 12)
    exp_year  = r.randint(now.year, now.year + 5)

    merchant  = r.choice(MERCHANT_DATA)
    m_id, m_name, m_city, m_state, mcc, acq_bin = merchant

    terminal  = "T" + "".join(r.choices(string.digits, k=7))
    amount    = round(r.uniform(1.00, 4999.99), 2)
    currency  = r.choice(CURRENCIES)
    rate      = EXCHANGE_RATES.get(currency, 1.0)
    txn_curr_amount = round(amount / rate, 2)

    response  = _weighted_choice(RESPONSE_WEIGHTS)
    approved  = response in APPROVED_CODES
    status    = "APPROVED" if approved else "DECLINED"
    txn_type  = r.choices(
        ["PURCHASE", "AUTH_ONLY", "CAPTURE", "REFUND", "VOID"],
        weights=[70, 12, 10, 5, 3]
    )[0]
    auth_ts   = now + timedelta(milliseconds=r.randint(80, 2500)) if approved else None

    # CVV / AVS only meaningful for ECOMMERCE or MANUAL
    cvv_result = None
    avs_result = None
    if entry in ("ECOMMERCE", "MANUAL"):
        cvv_result = r.choices(["M", "N", "P", "U"], weights=[85, 8, 4, 3])[0]
        avs_result = r.choices(["Y", "N", "A", "Z", "S", "U", "R"],
                                weights=[60, 10, 10, 8, 5, 4, 3])[0]

    is_3ds     = (entry == "ECOMMERCE") and r.random() < 0.65
    fraud_flag = r.random() < 0.003          # 0.3% fraud rate
    fraud_score = round(r.betavariate(0.5, 8), 4) if fraud_flag else round(r.betavariate(0.3, 10), 4)

    fn = r.choice(FIRST_NAMES)
    ln = r.choice(LAST_NAMES)

    return {
        "pan":                     pan,
        "pan_masked":              mask_pan(pan),
        "pan_token":               generate_token(),
        "network_id":              CARD_NETWORKS[network]["id"],
        "card_type":               card_type,
        "expiry_month":            exp_month,
        "expiry_year":             exp_year,
        "cardholder_name":         f"{fn} {ln}",
        "retrieval_ref_num":       _rrn(),
        "system_trace_audit_num":  _stan(),
        "auth_code":               _auth_code() if approved else None,
        "merchant_id":             m_id,
        "merchant_name":           m_name,
        "merchant_city":           m_city,
        "merchant_state":          m_state,
        "merchant_country":        "USA",
        "mcc":                     mcc,
        "terminal_id":             terminal,
        "acquirer_bin":            acq_bin,
        "txn_type":                txn_type,
        "entry_mode":              entry,
        "txn_amount":              amount,
        "currency_code":           currency,
        "txn_currency_amount":     txn_curr_amount,
        "exchange_rate":           rate,
        "response_code":           response,
        "txn_status":              status,
        "is_partial_approval":     0,
        "approved_amount":         amount if approved else None,
        "cvv_result":              cvv_result,
        "avs_result":              avs_result,
        "is_3ds":                  1 if is_3ds else 0,
        "is_fraud_flag":           1 if fraud_flag else 0,
        "fraud_score":             fraud_score,
        "txn_timestamp":           now,
        "auth_timestamp":          auth_ts,
        "settlement_timestamp":    None,
        "original_txn_id":         None,
    }


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

INSERT_SQL = """
INSERT INTO dbo.card_transaction (
    pan, pan_masked, pan_token, network_id, card_type,
    expiry_month, expiry_year, cardholder_name,
    retrieval_ref_num, system_trace_audit_num, auth_code,
    merchant_id, merchant_name, merchant_city, merchant_state,
    merchant_country, mcc, terminal_id, acquirer_bin,
    txn_type, entry_mode, txn_amount, currency_code,
    txn_currency_amount, exchange_rate, response_code, txn_status,
    is_partial_approval, approved_amount, cvv_result, avs_result,
    is_3ds, is_fraud_flag, fraud_score,
    txn_timestamp, auth_timestamp, settlement_timestamp, original_txn_id
) OUTPUT INSERTED.txn_id
VALUES (
    ?,?,?,?,?,
    ?,?,?,
    ?,?,?,
    ?,?,?,?,
    ?,?,?,?,
    ?,?,?,?,
    ?,?,?,?,
    ?,?,?,?,
    ?,?,?,
    ?,?,?,?
);
"""

UPDATE_STATUS_SQL = """
UPDATE dbo.card_transaction
SET txn_status  = ?,
    updated_at  = SYSUTCDATETIME()
WHERE txn_id = ?;
"""

UPDATE_SETTLE_SQL = """
UPDATE dbo.card_transaction
SET txn_status           = 'SETTLED',
    settlement_timestamp = SYSUTCDATETIME(),
    updated_at           = SYSUTCDATETIME()
WHERE txn_id = ?;
"""

UPDATE_FRAUD_SQL = """
UPDATE dbo.card_transaction
SET is_fraud_flag = 1,
    fraud_score   = ?,
    updated_at    = SYSUTCDATETIME()
WHERE txn_id = ?;
"""

REVERSE_SQL = """
INSERT INTO dbo.card_transaction (
    pan, pan_masked, pan_token, network_id, card_type,
    expiry_month, expiry_year, cardholder_name,
    retrieval_ref_num, system_trace_audit_num, auth_code,
    merchant_id, merchant_name, merchant_city, merchant_state,
    merchant_country, mcc, terminal_id, acquirer_bin,
    txn_type, entry_mode, txn_amount, currency_code,
    txn_currency_amount, exchange_rate, response_code, txn_status,
    is_partial_approval, approved_amount, cvv_result, avs_result,
    is_3ds, is_fraud_flag, fraud_score,
    txn_timestamp, auth_timestamp, settlement_timestamp, original_txn_id
) OUTPUT INSERTED.txn_id
SELECT
    pan, pan_masked, pan_token, network_id, card_type,
    expiry_month, expiry_year, cardholder_name,
    ?, ?, NULL,
    merchant_id, merchant_name, merchant_city, merchant_state,
    merchant_country, mcc, terminal_id, acquirer_bin,
    'VOID', entry_mode, txn_amount, currency_code,
    txn_currency_amount, exchange_rate, '00', 'REVERSED',
    0, NULL, NULL, NULL,
    0, 0, 0.0,
    SYSUTCDATETIME(), NULL, NULL, ?
FROM dbo.card_transaction
WHERE txn_id = ?;
"""

CDC_CAPTURE_PROBE_SQL = """
SELECT TOP 1 __$start_lsn
FROM cdc.dbo_card_transaction_CT
WHERE txn_id = ?
ORDER BY __$start_lsn DESC;
"""

LOG_SPACE_SQL = """
SELECT
    database_id,
    DB_NAME(database_id)        AS db_name,
    total_log_size_mb           = total_log_size_bytes / 1048576.0,
    used_log_space_mb           = used_log_space_bytes / 1048576.0,
    used_log_space_pct          = used_log_space_percent
FROM sys.dm_db_log_space_usage;
"""

CPU_SQL = """
SELECT TOP 1
    record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]','int') AS sql_cpu_pct
FROM (
    SELECT CAST(record AS XML) AS record
    FROM sys.dm_os_ring_buffers
    WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'
      AND record LIKE '%<ProcessUtilization>%'
) AS ring_data
ORDER BY record.value('(./Record/@id)[1]','bigint') DESC;
"""

IO_SQL = """
SELECT
    SUM(io_stall_read_ms)   AS total_read_stall_ms,
    SUM(io_stall_write_ms)  AS total_write_stall_ms,
    SUM(num_of_reads)       AS total_reads,
    SUM(num_of_writes)      AS total_writes,
    SUM(num_of_bytes_read)  AS total_bytes_read,
    SUM(num_of_bytes_written) AS total_bytes_written
FROM sys.dm_io_virtual_file_stats(DB_ID(), NULL);
"""


def try_connect(server, database, user, password) -> pyodbc.Connection:
    drivers = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 13 for SQL Server",
        "SQL Server",
    ]
    for drv in drivers:
        try:
            conn = pyodbc.connect(
                f"DRIVER={{{drv}}};SERVER={server};DATABASE={database};"
                f"UID={user};PWD={password};TrustServerCertificate=yes;",
                autocommit=False,
                timeout=10,
            )
            return conn
        except pyodbc.Error:
            continue
    raise RuntimeError("No working ODBC driver found. Install ODBC Driver 17 or 18 for SQL Server.")


# ---------------------------------------------------------------------------
# Metrics collector (background thread)
# ---------------------------------------------------------------------------

@dataclass
class MetricsSample:
    ts: float
    sql_cpu_pct: Optional[float]
    log_used_mb: Optional[float]
    log_total_mb: Optional[float]
    total_writes: Optional[int]
    total_reads: Optional[int]


class MetricsCollector(threading.Thread):
    def __init__(self, conn_factory, interval: float = 1.0):
        super().__init__(daemon=True, name="MetricsCollector")
        self._factory  = conn_factory
        self._interval = interval
        self._samples: list[MetricsSample] = []
        self._stop     = threading.Event()

    def run(self):
        conn = self._factory()
        cur  = conn.cursor()
        while not self._stop.is_set():
            try:
                cpu = log_u = log_t = writes = reads = None

                cur.execute(CPU_SQL)
                row = cur.fetchone()
                if row:
                    cpu = float(row[0])

                cur.execute(LOG_SPACE_SQL)
                row = cur.fetchone()
                if row:
                    log_t, log_u = float(row[2]), float(row[3])

                cur.execute(IO_SQL)
                row = cur.fetchone()
                if row:
                    reads, writes = int(row[2] or 0), int(row[3] or 0)

                self._samples.append(MetricsSample(
                    ts=time.monotonic(),
                    sql_cpu_pct=cpu,
                    log_used_mb=log_u,
                    log_total_mb=log_t,
                    total_writes=writes,
                    total_reads=reads,
                ))
            except Exception:
                pass
            self._stop.wait(self._interval)
        conn.close()

    def stop(self):
        self._stop.set()

    @property
    def samples(self):
        return list(self._samples)


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

@dataclass
class WorkerStats:
    inserts:    int = 0
    updates:    int = 0
    reversals:  int = 0
    errors:     int = 0
    latencies:  list = field(default_factory=list)   # seconds


class Worker(threading.Thread):
    def __init__(self, worker_id: int, conn_factory, stop_event: threading.Event,
                 id_pool: queue.Queue, rate_limiter, args):
        super().__init__(daemon=True, name=f"Worker-{worker_id}")
        self._wid      = worker_id
        self._factory  = conn_factory
        self._stop     = stop_event
        self._id_pool  = id_pool
        self._limiter  = rate_limiter
        self._args     = args
        self.stats     = WorkerStats()
        self._rng      = random.Random()

    def run(self):
        conn = self._factory()
        cur  = conn.cursor()
        while not self._stop.is_set():
            self._limiter.acquire()
            try:
                roll = self._rng.random()
                t0   = time.monotonic()

                if roll < 0.70:
                    # INSERT new transaction
                    txn = build_card_transaction(self._rng)
                    params = (
                        txn["pan"], txn["pan_masked"], txn["pan_token"],
                        txn["network_id"], txn["card_type"],
                        txn["expiry_month"], txn["expiry_year"],
                        txn["cardholder_name"],
                        txn["retrieval_ref_num"], txn["system_trace_audit_num"],
                        txn["auth_code"],
                        txn["merchant_id"], txn["merchant_name"],
                        txn["merchant_city"], txn["merchant_state"],
                        txn["merchant_country"], txn["mcc"],
                        txn["terminal_id"], txn["acquirer_bin"],
                        txn["txn_type"], txn["entry_mode"],
                        txn["txn_amount"], txn["currency_code"],
                        txn["txn_currency_amount"], txn["exchange_rate"],
                        txn["response_code"], txn["txn_status"],
                        txn["is_partial_approval"], txn["approved_amount"],
                        txn["cvv_result"], txn["avs_result"],
                        txn["is_3ds"], txn["is_fraud_flag"],
                        txn["fraud_score"],
                        txn["txn_timestamp"], txn["auth_timestamp"],
                        txn["settlement_timestamp"], txn["original_txn_id"],
                    )
                    cur.execute(INSERT_SQL, params)
                    row = cur.fetchone()
                    conn.commit()
                    elapsed = time.monotonic() - t0
                    self.stats.inserts   += 1
                    self.stats.latencies.append(elapsed)
                    if row:
                        try:
                            self._id_pool.put_nowait(int(row[0]))
                        except queue.Full:
                            pass

                elif roll < 0.85:
                    # UPDATE status → SETTLED
                    try:
                        txn_id = self._id_pool.get_nowait()
                    except queue.Empty:
                        continue
                    cur.execute(UPDATE_SETTLE_SQL, txn_id)
                    conn.commit()
                    elapsed = time.monotonic() - t0
                    self.stats.updates   += 1
                    self.stats.latencies.append(elapsed)

                elif roll < 0.93:
                    # UPDATE fraud flag
                    try:
                        txn_id = self._id_pool.get_nowait()
                    except queue.Empty:
                        continue
                    score  = round(self._rng.uniform(0.7, 1.0), 4)
                    cur.execute(UPDATE_FRAUD_SQL, (score, txn_id))
                    conn.commit()
                    elapsed = time.monotonic() - t0
                    self.stats.updates   += 1
                    self.stats.latencies.append(elapsed)

                else:
                    # INSERT reversal (VOID)
                    try:
                        orig_id = self._id_pool.get_nowait()
                    except queue.Empty:
                        continue
                    cur.execute(REVERSE_SQL, (_rrn(), _stan(), orig_id, orig_id))
                    row = cur.fetchone()
                    conn.commit()
                    elapsed = time.monotonic() - t0
                    self.stats.reversals += 1
                    self.stats.latencies.append(elapsed)
                    if row:
                        try:
                            self._id_pool.put_nowait(int(row[0]))
                        except queue.Full:
                            pass

            except Exception as exc:
                try:
                    conn.rollback()
                except Exception:
                    pass
                self.stats.errors += 1
        conn.close()


# ---------------------------------------------------------------------------
# Rate limiter (token bucket)
# ---------------------------------------------------------------------------

class TokenBucket:
    def __init__(self, rate: float):
        self._rate     = rate          # tokens per second
        self._tokens   = rate
        self._last     = time.monotonic()
        self._lock     = threading.Lock()

    def acquire(self):
        while True:
            with self._lock:
                now    = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
                self._last   = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            time.sleep(0.001)


# ---------------------------------------------------------------------------
# CDC capture latency probe
# ---------------------------------------------------------------------------

def measure_cdc_capture_latency(conn_factory, n: int = 5, timeout: float = 30.0) -> list[float]:
    """Insert probe rows and measure how long until they appear in _CT table."""
    latencies = []
    conn = conn_factory()
    cur  = conn.cursor()
    for _ in range(n):
        txn = build_card_transaction()
        params = (
            txn["pan"], txn["pan_masked"], txn["pan_token"],
            txn["network_id"], txn["card_type"],
            txn["expiry_month"], txn["expiry_year"],
            txn["cardholder_name"],
            txn["retrieval_ref_num"], txn["system_trace_audit_num"],
            txn["auth_code"],
            txn["merchant_id"], txn["merchant_name"],
            txn["merchant_city"], txn["merchant_state"],
            txn["merchant_country"], txn["mcc"],
            txn["terminal_id"], txn["acquirer_bin"],
            txn["txn_type"], txn["entry_mode"],
            txn["txn_amount"], txn["currency_code"],
            txn["txn_currency_amount"], txn["exchange_rate"],
            txn["response_code"], txn["txn_status"],
            txn["is_partial_approval"], txn["approved_amount"],
            txn["cvv_result"], txn["avs_result"],
            txn["is_3ds"], txn["is_fraud_flag"],
            txn["fraud_score"],
            txn["txn_timestamp"], txn["auth_timestamp"],
            txn["settlement_timestamp"], txn["original_txn_id"],
        )
        cur.execute(INSERT_SQL, params)
        row = cur.fetchone()
        conn.commit()
        if not row:
            continue
        txn_id = int(row[0])
        t0 = time.monotonic()
        deadline = t0 + timeout
        while time.monotonic() < deadline:
            try:
                cur.execute(CDC_CAPTURE_PROBE_SQL, txn_id)
                if cur.fetchone():
                    latencies.append(time.monotonic() - t0)
                    break
            except Exception:
                pass
            time.sleep(0.05)
    conn.close()
    return latencies


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _pct(data: list[float], p: int) -> float:
    if not data:
        return 0.0
    return statistics.quantiles(data, n=100)[p - 1]


def print_report(args, phase_label: str, duration: float,
                 workers: list[Worker], metrics: list[MetricsSample],
                 cdc_latencies: list[float]):

    all_lat = []
    total_ins = total_upd = total_rev = total_err = 0
    for w in workers:
        all_lat.extend(w.stats.latencies)
        total_ins += w.stats.inserts
        total_upd += w.stats.updates
        total_rev += w.stats.reversals
        total_err += w.stats.errors

    total_ops = total_ins + total_upd + total_rev
    tps        = total_ops / duration if duration > 0 else 0

    cpu_vals  = [s.sql_cpu_pct for s in metrics if s.sql_cpu_pct is not None]
    log_vals  = [s.log_used_mb for s in metrics if s.log_used_mb is not None]
    io_writes = [s.total_writes for s in metrics if s.total_writes is not None]

    log_start = log_vals[0]  if log_vals else 0
    log_end   = log_vals[-1] if log_vals else 0
    log_growth = log_end - log_start

    write_start = io_writes[0]  if len(io_writes) >= 2 else 0
    write_end   = io_writes[-1] if len(io_writes) >= 2 else 0
    write_delta = write_end - write_start

    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  {phase_label}")
    print(sep)
    print(f"  Duration         : {duration:.1f}s")
    print(f"  Threads          : {len(workers)}")
    print(f"  Target TPS       : {args.tps}")
    print()
    print(f"  Throughput")
    print(f"    Actual TPS     : {tps:.1f}")
    print(f"    Total ops      : {total_ops:,}  (ins={total_ins:,} upd={total_upd:,} rev={total_rev:,})")
    print(f"    Errors         : {total_err}")
    print()
    print(f"  Latency (commit round-trip)")
    if all_lat:
        print(f"    p50            : {_pct(all_lat,50)*1000:.1f} ms")
        print(f"    p95            : {_pct(all_lat,95)*1000:.1f} ms")
        print(f"    p99            : {_pct(all_lat,99)*1000:.1f} ms")
        print(f"    max            : {max(all_lat)*1000:.1f} ms")
    print()
    print(f"  SQL Server CPU   : avg {statistics.mean(cpu_vals):.1f}%  max {max(cpu_vals):.1f}%"
          if cpu_vals else "  SQL Server CPU   : n/a")
    print(f"  Log growth       : {log_growth:+.1f} MB  "
          f"(start {log_start:.1f} MB → end {log_end:.1f} MB)")
    print(f"  Write I/Os delta : {write_delta:,}")
    print()
    if cdc_latencies:
        print(f"  CDC Capture Lag")
        print(f"    mean           : {statistics.mean(cdc_latencies)*1000:.0f} ms")
        print(f"    max            : {max(cdc_latencies)*1000:.0f} ms")
        print(f"    samples        : {len(cdc_latencies)}")
    else:
        print("  CDC Capture Lag  : not measured (CDC may not be enabled)")
    print(sep)

    return {
        "phase":           phase_label,
        "duration_s":      round(duration, 2),
        "threads":         len(workers),
        "target_tps":      args.tps,
        "actual_tps":      round(tps, 2),
        "total_ops":       total_ops,
        "inserts":         total_ins,
        "updates":         total_upd,
        "reversals":       total_rev,
        "errors":          total_err,
        "latency_p50_ms":  round(_pct(all_lat, 50) * 1000, 2) if all_lat else None,
        "latency_p95_ms":  round(_pct(all_lat, 95) * 1000, 2) if all_lat else None,
        "latency_p99_ms":  round(_pct(all_lat, 99) * 1000, 2) if all_lat else None,
        "latency_max_ms":  round(max(all_lat) * 1000, 2) if all_lat else None,
        "cpu_avg_pct":     round(statistics.mean(cpu_vals), 2) if cpu_vals else None,
        "cpu_max_pct":     round(max(cpu_vals), 2) if cpu_vals else None,
        "log_start_mb":    round(log_start, 2),
        "log_end_mb":      round(log_end, 2),
        "log_growth_mb":   round(log_growth, 2),
        "write_io_delta":  write_delta,
        "cdc_lag_mean_ms": round(statistics.mean(cdc_latencies) * 1000, 2) if cdc_latencies else None,
        "cdc_lag_max_ms":  round(max(cdc_latencies) * 1000, 2) if cdc_latencies else None,
    }


# ---------------------------------------------------------------------------
# Run a phase
# ---------------------------------------------------------------------------

def run_phase(label: str, args, conn_factory, with_cdc: bool = False) -> dict:
    print(f"\n>>> Phase: {label}  (duration={args.duration}s  threads={args.threads}  tps={args.tps})")

    id_pool   = queue.Queue(maxsize=50_000)
    stop_evt  = threading.Event()
    limiter   = TokenBucket(float(args.tps))

    mc = MetricsCollector(conn_factory)
    mc.start()

    workers = [
        Worker(i, conn_factory, stop_evt, id_pool, limiter, args)
        for i in range(args.threads)
    ]
    t_start = time.monotonic()
    for w in workers:
        w.start()

    # Progress bar
    for elapsed in range(1, args.duration + 1):
        time.sleep(1)
        done = sum(w.stats.inserts + w.stats.updates + w.stats.reversals for w in workers)
        print(f"  [{elapsed:4d}/{args.duration}s]  ops={done:,}", end="\r")

    stop_evt.set()
    for w in workers:
        w.join(timeout=10)

    t_end    = time.monotonic()
    duration = t_end - t_start
    mc.stop()
    mc.join(timeout=5)

    # CDC capture latency
    cdc_lats = []
    if with_cdc:
        print("\n  Probing CDC capture latency...")
        try:
            cdc_lats = measure_cdc_capture_latency(conn_factory, n=5)
        except Exception as e:
            print(f"  CDC probe skipped: {e}")

    return print_report(args, label, duration, workers, mc.samples, cdc_lats)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Card payment CDC hammer for SQL Server")
    ap.add_argument("--server",   default="localhost", help="SQL Server host")
    ap.add_argument("--database", default="CDC_BENCHMARK_DB")
    ap.add_argument("--user",     default="sa")
    ap.add_argument("--password", required=True)
    ap.add_argument("--duration", type=int, default=60,  help="seconds per phase")
    ap.add_argument("--threads",  type=int, default=8,   help="concurrent worker threads")
    ap.add_argument("--tps",      type=int, default=300, help="target transactions/sec")
    ap.add_argument("--skip-cdc-phase", action="store_true",
                    help="Skip the CDC-enabled phase (run baseline only)")
    ap.add_argument("--no-cleanup", action="store_true",
                    help="Leave card_transaction rows after the run")
    ap.add_argument("--output-dir", default=".", help="Directory for output files")
    ap.add_argument("--confirm", action="store_true",
                    help="Required safety flag — confirms you are NOT on a production server")
    args = ap.parse_args()

    if not args.confirm:
        print("\n*** SAFETY GATE ***")
        print("This script generates high-volume DML against SQL Server.")
        print("Re-run with --confirm to proceed (confirms non-production target).")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    def conn_factory():
        return try_connect(args.server, args.database, args.user, args.password)

    # Verify connectivity and table presence
    try:
        conn = conn_factory()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='card_transaction'")
        if cur.fetchone()[0] == 0:
            print("\nERROR: dbo.card_transaction not found.")
            print("Run card_payments_schema.sql first to create the table.")
            sys.exit(1)
        conn.close()
    except Exception as e:
        print(f"\nERROR connecting: {e}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("  Card Payment CDC Hammer")
    print(f"  Server  : {args.server}  DB: {args.database}")
    print(f"  Threads : {args.threads}   Duration: {args.duration}s/phase   Target TPS: {args.tps}")
    print("=" * 70)

    results = []

    # -----------------------------------------------------------------------
    # Phase 1: Baseline (no CDC — ensure CDC is disabled before running)
    # -----------------------------------------------------------------------
    results.append(run_phase("Phase 1 — Baseline (no CDC)", args, conn_factory, with_cdc=False))

    if not args.skip_cdc_phase:
        print("\n>>> Enable CDC on dbo.card_transaction now, then press ENTER to continue...")
        print("    EXEC sys.sp_cdc_enable_db;")
        print("    EXEC sys.sp_cdc_enable_table @source_schema=N'dbo',")
        print("         @source_name=N'card_transaction', @role_name=NULL,")
        print("         @supports_net_changes=1;")
        input()

        # -------------------------------------------------------------------
        # Phase 2: CDC enabled
        # -------------------------------------------------------------------
        results.append(run_phase("Phase 2 — CDC Enabled", args, conn_factory, with_cdc=True))

    # -----------------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------------
    if not args.no_cleanup:
        print("\n>>> Cleaning up test rows...")
        conn = conn_factory()
        cur  = conn.cursor()
        cur.execute("DELETE FROM dbo.card_transaction")
        conn.commit()
        conn.close()
        print("    Done.")

    # -----------------------------------------------------------------------
    # Write outputs
    # -----------------------------------------------------------------------
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON summary
    summary_path = os.path.join(args.output_dir, f"card_cdc_hammer_{ts}.json")
    with open(summary_path, "w") as f:
        json.dump({"run_ts": ts, "args": vars(args), "phases": results}, f, indent=2)

    # CSV
    csv_path = os.path.join(args.output_dir, f"card_cdc_hammer_{ts}.csv")
    if results:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    print(f"\n  Results → {summary_path}")
    print(f"  CSV     → {csv_path}")

    # Side-by-side delta if two phases
    if len(results) == 2:
        b, c = results[0], results[1]
        print("\n" + "=" * 70)
        print("  DELTA: CDC vs Baseline")
        print("=" * 70)
        def delta(key, fmt=".1f", suffix=""):
            bv = b.get(key) or 0
            cv = c.get(key) or 0
            d  = cv - bv
            pct = (d / bv * 100) if bv else 0
            print(f"  {key:<28} baseline={bv:{fmt}}{suffix}  cdc={cv:{fmt}}{suffix}  delta={d:+{fmt}}{suffix}  ({pct:+.1f}%)")
        delta("actual_tps")
        delta("latency_p50_ms", ".1f", " ms")
        delta("latency_p95_ms", ".1f", " ms")
        delta("latency_p99_ms", ".1f", " ms")
        delta("latency_max_ms", ".1f", " ms")
        delta("cpu_avg_pct",    ".1f", "%")
        delta("log_growth_mb",  ".1f", " MB")
        print("=" * 70)


if __name__ == "__main__":
    main()
