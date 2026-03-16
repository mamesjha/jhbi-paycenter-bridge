#!/usr/bin/env python3
"""
=============================================================================
  Payment Message Generator
  Zelle  |  FedNow  |  RTP (The Clearing House)
  Uses the Faker library to produce realistic synthetic payment messages
=============================================================================

INSTALL
-------
  pip install faker

USAGE
-----
  # Generate 10 of every message type for all three networks:
  python generate_payments.py

  # Generate 50 FedNow credit transfers only:
  python generate_payments.py --network fednow --type credit_transfer --count 50

  # Generate 100 mixed Zelle messages, write to custom dir:
  python generate_payments.py --network zelle --count 100 --output-dir ./test_data

  # Generate all types, 25 each, as a single combined JSONL file:
  python generate_payments.py --count 25 --format jsonl

  # Dry-run: print one sample of each to stdout:
  python generate_payments.py --count 1 --dry-run

AVAILABLE NETWORKS / TYPES
---------------------------
  fednow:  credit_transfer  payment_status  return  rfp  rfp_response  liquidity
  rtp:     credit_transfer  payment_status  return  rfp  rfp_response
  zelle:   send_payment     payment_status  cancellation

OUTPUT
------
  Generated files are written to --output-dir (default: ./generated_payments/)
  Each file is named  {network}_{type}_{timestamp}.json  or  .jsonl
=============================================================================
"""

import argparse
import json
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

try:
    from faker import Faker
    from faker.providers import bank, company, address, person, internet, phone_number
except ImportError:
    print("ERROR: Faker is not installed.  Run:  pip install faker")
    sys.exit(1)

# ── Faker setup ──────────────────────────────────────────────────────────────
fake = Faker("en_US")
Faker.seed(0)   # Remove or change for different runs

# ═══════════════════════════════════════════════════════════════════════════
#  REFERENCE DATA
#  Real bank names / routing numbers for realism
# ═══════════════════════════════════════════════════════════════════════════

BANKS = [
    {"name": "JPMorgan Chase Bank, N.A.",      "aba": "021000021", "bic": "CHASUS33"},
    {"name": "Bank of America, N.A.",           "aba": "021000089", "bic": "BOFAUS3N"},
    {"name": "Wells Fargo Bank, N.A.",          "aba": "122000247", "bic": "WFBIUS6S"},
    {"name": "Citibank, N.A.",                  "aba": "026009593", "bic": "CITIUS33"},
    {"name": "U.S. Bank N.A.",                  "aba": "091000022", "bic": "USBKUS44"},
    {"name": "Truist Bank",                     "aba": "053000219", "bic": "BRBTUS33"},
    {"name": "PNC Bank, N.A.",                  "aba": "043000096", "bic": "PNCCUS33"},
    {"name": "Capital One, N.A.",               "aba": "051405515", "bic": "HIBKUS44"},
    {"name": "TD Bank, N.A.",                   "aba": "011103093", "bic": "NRTHUS33"},
    {"name": "Goldman Sachs Bank USA",          "aba": "124085066", "bic": "GSCMUS33"},
    {"name": "Morgan Stanley Bank, N.A.",       "aba": "124071889", "bic": "MSNYUS33"},
    {"name": "Silicon Valley Bank",             "aba": "121140399", "bic": "SVBKUS6S"},
    {"name": "First Republic Bank",             "aba": "321081669", "bic": "FRBBUS6S"},
    {"name": "Ally Bank",                       "aba": "124003116", "bic": "ALLBUS33"},
    {"name": "Regions Bank",                    "aba": "062000019", "bic": "UPNBUS44"},
]

PURPOSE_CODES = {
    "SUPP": "Supplier Payment",
    "SALA": "Salary Payment",
    "BEXP": "Business Expenses",
    "GDDS": "Goods and Services",
    "TAXS": "Tax Payment",
    "TREA": "Treasury Payment",
    "INTC": "Intracompany Transfer",
    "REFU": "Refund",
    "DIVI": "Dividend",
    "LOAN": "Loan Repayment",
}

FEDNOW_REJECT_CODES = ["AC01", "AC04", "AC06", "AG01", "AM04", "AM05", "NARR"]
RTP_REJECT_CODES    = ["AC01", "AC04", "AC06", "AG01", "AM04", "AM05", "ACTC", "NARR"]
RETURN_REASON_CODES = ["AC04", "AM09", "CUST", "DUPL", "MD06", "FRAD", "NARR"]
ZELLE_ERROR_CODES   = [
    "DAILY_LIMIT_EXCEEDED", "MONTHLY_LIMIT_EXCEEDED", "INSUFFICIENT_FUNDS",
    "INVALID_TOKEN", "ACCOUNT_RESTRICTED", "DUPLICATE_PAYMENT",
    "FRAUD_BLOCKED", "RECIPIENT_NOT_ENROLLED_EXPIRED", "SERVICE_UNAVAILABLE",
]
ACCOUNT_TYPES = ["CACC", "SVGS", "TRAN"]
ZELLE_TOKEN_TYPES = ["EMAL", "PHON"]

# ═══════════════════════════════════════════════════════════════════════════
#  PRIMITIVE GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def uetr() -> str:
    """Generate a UUID v4 — mandatory on all ISO 20022 messages."""
    return str(uuid.uuid4())


def msg_id(prefix: str, ts: datetime) -> str:
    """Generate a realistic message ID: PREFIX + YYYYMMDD + 10-digit seq."""
    seq = random.randint(1000000000, 9999999999)
    return f"{prefix}{ts.strftime('%Y%m%d')}{seq}"


def biz_date(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d")


def iso_ts(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def rand_ts(within_days: int = 0) -> datetime:
    """Random timestamp within the last N days (or today if 0)."""
    base = now_utc().replace(microsecond=0)
    if within_days:
        offset = timedelta(days=random.randint(0, within_days),
                           hours=random.randint(0, 23),
                           minutes=random.randint(0, 59),
                           seconds=random.randint(0, 59))
        base = base - offset
    return base.replace(microsecond=random.randint(0, 999) * 1000)


def rand_account() -> str:
    """16-digit account number."""
    return str(random.randint(1000000000000000, 9999999999999999))


def rand_amount(lo: float = 1.00, hi: float = 500000.00) -> str:
    """Random dollar amount formatted to 2dp as string."""
    return f"{random.uniform(lo, hi):.2f}"


def rand_amount_float(lo: float = 1.00, hi: float = 500000.00) -> float:
    return round(random.uniform(lo, hi), 2)


def rand_bank(exclude: Optional[Dict] = None) -> Dict:
    choices = [b for b in BANKS if b != exclude]
    return random.choice(choices)


def rand_purpose() -> str:
    return random.choice(list(PURPOSE_CODES.keys()))


def rand_tax_id() -> str:
    return f"{random.randint(10,99)}-{random.randint(1000000,9999999)}"


def rand_invoice_refs(n: int = None) -> List[Dict]:
    count = n or random.randint(1, 3)
    refs = []
    for i in range(count):
        ref_date = (now_utc() - timedelta(days=random.randint(7, 60))).strftime("%Y-%m-%d")
        refs.append({
            "Tp": {"CdOrPrtry": {"Cd": "CINV"}},
            "Nb": f"INV-{now_utc().year}-{random.randint(1000,9999)}",
            "RltdDt": ref_date,
        })
    return refs


def _party_org(name: str, tax_id: str) -> Dict:
    return {
        "Nm": name,
        "PstlAdr": {
            "StrtNm": fake.street_address(),
            "TwnNm": fake.city(),
            "CtrySubDvsn": fake.state_abbr(),
            "PstCd": fake.zipcode(),
            "Ctry": "US",
        },
        "Id": {"OrgId": {"Othr": {"Id": tax_id, "SchmeNm": {"Cd": "TXID"}}}},
        "CtryOfRes": "US",
    }


def _party_person(name: str) -> Dict:
    parts = name.split()
    return {
        "Nm": name,
        "PstlAdr": {
            "StrtNm": fake.street_address(),
            "TwnNm": fake.city(),
            "CtrySubDvsn": fake.state_abbr(),
            "PstCd": fake.zipcode(),
            "Ctry": "US",
        },
        "Id": {
            "PrvtId": {
                "Othr": {
                    "Id": fake.ssn().replace("-", ""),
                    "SchmeNm": {"Cd": "SOSE"},
                }
            }
        },
    }


def _account(acct_num: str) -> Dict:
    acct_type = random.choice(ACCOUNT_TYPES)
    return {
        "Id": {"Othr": {"Id": acct_num, "SchmeNm": {"Cd": "BBAN"}}},
        "Tp": {"Cd": acct_type},
        "Ccy": "USD",
    }


def _fi(bank: Dict) -> Dict:
    return {
        "FinInstnId": {
            "ClrSysMmbId": {
                "ClrSysId": {"Cd": "USABA"},
                "MmbId": bank["aba"],
            },
            "Nm": bank["name"],
        }
    }


def _app_hdr(fr_bank: Dict, to_bank: Dict, biz_msg_id: str, msg_def: str, ts: datetime) -> Dict:
    return {
        "Fr": {"FIId": _fi(fr_bank)},
        "To": {"FIId": _fi(to_bank)},
        "BizMsgIdr": biz_msg_id,
        "MsgDefIdr": msg_def,
        "BizSvc": f"iso20022:xsd${msg_def}",
        "CreDtTm": iso_ts(ts),
        "PssblDplct": False,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  FEDNOW GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def fednow_credit_transfer() -> Dict[str, Any]:
    """Generate a FedNow pacs.008.001.08 credit transfer."""
    ts = rand_ts()
    sender_bank = rand_bank()
    receiver_bank = rand_bank(exclude=sender_bank)
    debtor_name = fake.company()
    creditor_name = fake.company()
    debtor_acct = rand_account()
    creditor_acct = rand_account()
    amount = rand_amount(100.00, 499999.00)
    amount_float = float(amount)
    purpose = rand_purpose()
    tx_id = msg_id("FEDNOW", ts)
    instr_id = msg_id(sender_bank["aba"][:4].upper(), ts)
    e2e_id = f"E2E-{fake.bothify('??##-####-???#').upper()}"
    u = uetr()

    iso = {
        "AppHdr": _app_hdr(sender_bank, receiver_bank, msg_id(sender_bank["aba"][:8], ts), "pacs.008.001.08", ts),
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08",
            "FIToFICstmrCdtTrf": {
                "GrpHdr": {
                    "MsgId": tx_id,
                    "CreDtTm": iso_ts(ts),
                    "NbOfTxs": "1",
                    "TtlIntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "IntrBkSttlmDt": biz_date(ts),
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "FDN"}},
                    "InstgAgt": _fi(sender_bank),
                    "InstdAgt": _fi(receiver_bank),
                },
                "CdtTrfTxInf": {
                    "PmtId": {
                        "InstrId": instr_id,
                        "EndToEndId": e2e_id,
                        "TxId": tx_id,
                        "UETR": u,
                    },
                    "IntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "IntrBkSttlmDt": biz_date(ts),
                    "InstdAmt": {"@Ccy": "USD", "#text": amount},
                    "ChrgBr": "SLEV",
                    "Dbtr": _party_org(debtor_name, rand_tax_id()),
                    "DbtrAcct": _account(debtor_acct),
                    "DbtrAgt": _fi(sender_bank),
                    "CdtrAgt": _fi(receiver_bank),
                    "Cdtr": _party_org(creditor_name, rand_tax_id()),
                    "CdtrAcct": _account(creditor_acct),
                    "Purp": {"Cd": purpose},
                    "RmtInf": {
                        "Ustrd": fake.sentence(nb_words=10),
                        "Strd": {"RfrdDocInf": rand_invoice_refs()},
                    },
                },
            },
        },
    }

    flat = {
        "network": "FedNow",
        "message_type": "Credit Transfer",
        "message_id": tx_id,
        "created_at": iso_ts(ts),
        "settlement_date": biz_date(ts),
        "settlement_network": "FDN",
        "payment": {
            "instruction_id": instr_id,
            "end_to_end_id": e2e_id,
            "transaction_id": tx_id,
            "uetr": u,
            "amount": amount_float,
            "currency": "USD",
            "purpose_code": purpose,
            "purpose_description": PURPOSE_CODES[purpose],
            "remittance_info": fake.sentence(nb_words=8),
        },
        "sender_bank": {"name": sender_bank["name"], "routing_number": sender_bank["aba"]},
        "debtor": {"name": debtor_name, "account_number": debtor_acct},
        "receiver_bank": {"name": receiver_bank["name"], "routing_number": receiver_bank["aba"]},
        "creditor": {"name": creditor_name, "account_number": creditor_acct},
    }

    return {
        "_metadata": {"network": "FedNow", "message_type": "pacs.008.001.08", "generated_at": iso_ts(now_utc())},
        "iso20022": iso,
        "flattened": flat,
    }


def fednow_payment_status(credit_transfer: Optional[Dict] = None, force_reject: bool = False) -> Dict[str, Any]:
    """Generate a FedNow pacs.002.001.10 — accept or reject."""
    ct = credit_transfer or fednow_credit_transfer()
    flat_ct = ct["flattened"]
    orig_ts_str = ct["iso20022"]["AppHdr"]["CreDtTm"]
    ts = rand_ts()
    # Status response is always AFTER the original message
    resp_ts = datetime.fromisoformat(orig_ts_str.replace("Z", "+00:00")) + timedelta(milliseconds=random.randint(500, 9999))

    rejected = force_reject or (random.random() < 0.15)   # 15% rejection rate
    status = "RJCT" if rejected else "ACCP"
    reason_code = random.choice(FEDNOW_REJECT_CODES) if rejected else None

    sender_bank = next(b for b in BANKS if b["aba"] == ct["iso20022"]["AppHdr"]["Fr"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"])
    receiver_bank = next(b for b in BANKS if b["aba"] == ct["iso20022"]["AppHdr"]["To"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"])

    orig_msg_id = ct["iso20022"]["Document"]["FIToFICstmrCdtTrf"]["GrpHdr"]["MsgId"]
    orig_e2e = flat_ct["payment"]["end_to_end_id"]
    orig_uetr = flat_ct["payment"]["uetr"]
    amount = flat_ct["payment"]["amount"]
    status_msg_id = msg_id("STSR", resp_ts)

    tx_sts: Dict = {
        "StsId": status_msg_id,
        "OrgnlInstrId": flat_ct["payment"]["instruction_id"],
        "OrgnlEndToEndId": orig_e2e,
        "OrgnlTxId": flat_ct["payment"]["transaction_id"],
        "OrgnlUETR": orig_uetr,
        "TxSts": status,
        "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "FDN"}},
    }
    if rejected:
        tx_sts["StsRsnInf"] = {
            "Rsn": {"Cd": reason_code},
            "AddtlInf": fake.sentence(nb_words=12),
        }
    else:
        tx_sts["AccptncDtTm"] = iso_ts(resp_ts)
        tx_sts["FctvIntrBkSttlmDt"] = biz_date(resp_ts)

    iso = {
        "AppHdr": _app_hdr(receiver_bank, sender_bank, msg_id(receiver_bank["aba"][:8], resp_ts), "pacs.002.001.10", resp_ts),
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10",
            "FIToFIPmtStsRpt": {
                "GrpHdr": {
                    "MsgId": status_msg_id,
                    "CreDtTm": iso_ts(resp_ts),
                    "InstgAgt": _fi(receiver_bank),
                    "InstdAgt": _fi(sender_bank),
                },
                "OrgnlGrpInfAndSts": {
                    "OrgnlMsgId": orig_msg_id,
                    "OrgnlMsgNmId": "pacs.008.001.08",
                    "OrgnlCreDtTm": orig_ts_str,
                    "OrgnlNbOfTxs": "1",
                    "GrpSts": status,
                },
                "TxInfAndSts": tx_sts,
            },
        },
    }

    return {
        "_metadata": {"network": "FedNow", "message_type": "pacs.002.001.10", "generated_at": iso_ts(now_utc())},
        "iso20022": iso,
        "flattened": {
            "network": "FedNow",
            "message_type": "Payment Status Report",
            "message_id": status_msg_id,
            "created_at": iso_ts(resp_ts),
            "original_uetr": orig_uetr,
            "original_amount": amount,
            "status": status,
            "status_description": "Accepted and posted" if not rejected else f"Rejected — {reason_code}",
            "turnaround_ms": int((resp_ts - datetime.fromisoformat(orig_ts_str.replace("Z", "+00:00"))).total_seconds() * 1000),
            "rejection_reason": reason_code,
            "reporting_bank": receiver_bank["name"],
        },
    }


def fednow_return(credit_transfer: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate a FedNow pacs.004.001.09 payment return."""
    ct = credit_transfer or fednow_credit_transfer()
    flat_ct = ct["flattened"]
    orig_ts_str = ct["iso20022"]["AppHdr"]["CreDtTm"]
    orig_settle = ct["iso20022"]["Document"]["FIToFICstmrCdtTrf"]["GrpHdr"]["IntrBkSttlmDt"]
    # Return next business day
    return_ts = datetime.fromisoformat(orig_ts_str.replace("Z", "+00:00")) + timedelta(days=random.randint(0, 2), hours=random.randint(0, 23))
    reason = random.choice(RETURN_REASON_CODES)
    rtr_id = msg_id("RTR", return_ts)

    sender_bank = next(b for b in BANKS if b["aba"] == ct["iso20022"]["AppHdr"]["Fr"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"])
    receiver_bank = next(b for b in BANKS if b["aba"] == ct["iso20022"]["AppHdr"]["To"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"])
    amount = ct["iso20022"]["Document"]["FIToFICstmrCdtTrf"]["GrpHdr"]["TtlIntrBkSttlmAmt"]["#text"]
    orig_msg_id = ct["iso20022"]["Document"]["FIToFICstmrCdtTrf"]["GrpHdr"]["MsgId"]

    iso = {
        "AppHdr": _app_hdr(receiver_bank, sender_bank, msg_id(receiver_bank["aba"][:8], return_ts), "pacs.004.001.09", return_ts),
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.004.001.09",
            "PmtRtr": {
                "GrpHdr": {
                    "MsgId": rtr_id,
                    "CreDtTm": iso_ts(return_ts),
                    "NbOfTxs": "1",
                    "TtlRtrdIntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "IntrBkSttlmDt": biz_date(return_ts),
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "FDN"}},
                    "InstgAgt": _fi(receiver_bank),
                    "InstdAgt": _fi(sender_bank),
                },
                "TxInf": {
                    "RtrId": rtr_id,
                    "OrgnlGrpInf": {"OrgnlMsgId": orig_msg_id, "OrgnlMsgNmId": "pacs.008.001.08", "OrgnlCreDtTm": orig_ts_str},
                    "OrgnlInstrId": flat_ct["payment"]["instruction_id"],
                    "OrgnlEndToEndId": flat_ct["payment"]["end_to_end_id"],
                    "OrgnlTxId": flat_ct["payment"]["transaction_id"],
                    "OrgnlUETR": flat_ct["payment"]["uetr"],
                    "OrgnlIntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "OrgnlIntrBkSttlmDt": orig_settle,
                    "RtrdIntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "IntrBkSttlmDt": biz_date(return_ts),
                    "RtrRsnInf": {
                        "Rsn": {"Cd": reason},
                        "AddtlInf": fake.sentence(nb_words=10),
                    },
                },
            },
        },
    }

    return {
        "_metadata": {"network": "FedNow", "message_type": "pacs.004.001.09", "generated_at": iso_ts(now_utc())},
        "iso20022": iso,
        "flattened": {
            "network": "FedNow",
            "message_type": "Payment Return",
            "return_id": rtr_id,
            "return_amount": float(amount),
            "return_currency": "USD",
            "return_reason_code": reason,
            "original_uetr": flat_ct["payment"]["uetr"],
            "original_settlement_date": orig_settle,
            "return_settlement_date": biz_date(return_ts),
            "returning_bank": receiver_bank["name"],
        },
    }


def fednow_rfp() -> Dict[str, Any]:
    """Generate a FedNow pain.013.001.07 Request for Payment."""
    ts = rand_ts()
    creditor_bank = rand_bank()
    debtor_bank = rand_bank(exclude=creditor_bank)
    creditor_name = fake.company()
    debtor_name = fake.company()
    creditor_acct = rand_account()
    debtor_acct = rand_account()
    amount = rand_amount(50.00, 100000.00)
    u = uetr()
    rfp_id = msg_id("RFP", ts)
    e2e_id = f"E2E-RFP-{fake.bothify('??##-####').upper()}"
    req_date = biz_date(ts)
    exp_date = biz_date(ts + timedelta(days=random.randint(1, 5)))

    iso = {
        "AppHdr": _app_hdr(creditor_bank, debtor_bank, msg_id(creditor_bank["aba"][:8], ts), "pain.013.001.07", ts),
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pain.013.001.07",
            "CdtrPmtActvtnReq": {
                "GrpHdr": {
                    "MsgId": rfp_id,
                    "CreDtTm": iso_ts(ts),
                    "NbOfTxs": "1",
                    "CtrlSum": amount,
                    "InitgPty": {"Nm": creditor_bank["name"], "Id": {"OrgId": {"AnyBIC": creditor_bank["bic"]}}},
                },
                "PmtInf": {
                    "PmtInfId": f"{rfp_id}PMT",
                    "PmtMtd": "TRF",
                    "ReqdExctnDt": {"Dt": req_date},
                    "XpryDt": {"Dt": exp_date},
                    "PmtTpInf": {"SvcLvl": {"Cd": "URGP"}, "LclInstrm": {"Prtry": "FEDNOW"}, "CtgyPurp": {"Cd": rand_purpose()}},
                    "Dbtr": _party_org(debtor_name, rand_tax_id()),
                    "DbtrAcct": _account(debtor_acct),
                    "DbtrAgt": _fi(debtor_bank),
                    "CdtTrfTxInf": {
                        "PmtId": {"InstrId": msg_id(creditor_bank["aba"][:4].upper(), ts), "EndToEndId": e2e_id, "UETR": u},
                        "Amt": {"InstdAmt": {"@Ccy": "USD", "#text": amount}},
                        "ChrgBr": "SLEV",
                        "CdtrAgt": _fi(creditor_bank),
                        "Cdtr": _party_org(creditor_name, rand_tax_id()),
                        "CdtrAcct": _account(creditor_acct),
                        "Purp": {"Cd": rand_purpose()},
                        "RmtInf": {"Ustrd": fake.sentence(nb_words=10)},
                    },
                },
            },
        },
    }

    return {
        "_metadata": {"network": "FedNow", "message_type": "pain.013.001.07", "generated_at": iso_ts(now_utc())},
        "iso20022": iso,
        "flattened": {
            "network": "FedNow",
            "message_type": "Request for Payment",
            "rfp_id": rfp_id,
            "uetr": u,
            "end_to_end_id": e2e_id,
            "requested_execution_date": req_date,
            "expiry_date": exp_date,
            "amount": float(amount),
            "currency": "USD",
            "creditor": {"name": creditor_name, "bank": creditor_bank["name"]},
            "debtor": {"name": debtor_name, "bank": debtor_bank["name"]},
        },
    }


def fednow_rfp_response(rfp: Optional[Dict] = None, force_reject: bool = False) -> Dict[str, Any]:
    """Generate a FedNow pain.014.001.07 RfP response."""
    rfp_doc = rfp or fednow_rfp()
    ts = rand_ts()
    rejected = force_reject or (random.random() < 0.20)
    status = "RJCT" if rejected else "ACCP"
    rfp_grp_hdr = rfp_doc["iso20022"]["Document"]["CdtrPmtActvtnReq"]["GrpHdr"]
    rfp_pmt_inf = rfp_doc["iso20022"]["Document"]["CdtrPmtActvtnReq"]["PmtInf"]
    flat_rfp = rfp_doc["flattened"]

    resp_id = msg_id("RFPSTS", ts)
    debtor_bank_aba = rfp_doc["iso20022"]["AppHdr"]["To"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"]
    creditor_bank_aba = rfp_doc["iso20022"]["AppHdr"]["Fr"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"]
    debtor_bank = next(b for b in BANKS if b["aba"] == debtor_bank_aba)
    creditor_bank = next(b for b in BANKS if b["aba"] == creditor_bank_aba)

    tx_sts: Dict = {
        "StsId": resp_id,
        "OrgnlInstrId": rfp_pmt_inf["CdtTrfTxInf"]["PmtId"]["InstrId"],
        "OrgnlEndToEndId": flat_rfp["end_to_end_id"],
        "OrgnlUETR": flat_rfp["uetr"],
        "TxSts": status,
    }
    if rejected:
        tx_sts["StsRsnInf"] = {"Rsn": {"Cd": random.choice(["CUST", "AM04", "NOAS", "AM02"])}, "AddtlInf": fake.sentence(nb_words=8)}
    else:
        tx_sts["AccptncDtTm"] = iso_ts(ts)

    iso = {
        "AppHdr": _app_hdr(debtor_bank, creditor_bank, msg_id(debtor_bank["aba"][:8], ts), "pain.014.001.07", ts),
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pain.014.001.07",
            "CdtrPmtActvtnReqStsRpt": {
                "GrpHdr": {"MsgId": resp_id, "CreDtTm": iso_ts(ts), "InitgPty": {"Nm": debtor_bank["name"]}},
                "OrgnlGrpInfAndSts": {"OrgnlMsgId": rfp_grp_hdr["MsgId"], "OrgnlMsgNmId": "pain.013.001.07", "GrpSts": status},
                "OrgnlPmtInfAndSts": {
                    "OrgnlPmtInfId": rfp_pmt_inf["PmtInfId"],
                    "PmtInfSts": status,
                    "TxInfAndSts": tx_sts,
                },
            },
        },
    }

    return {
        "_metadata": {"network": "FedNow", "message_type": "pain.014.001.07", "generated_at": iso_ts(now_utc())},
        "iso20022": iso,
        "flattened": {
            "network": "FedNow",
            "message_type": "RfP Response",
            "response_id": resp_id,
            "original_rfp_id": rfp_grp_hdr["MsgId"],
            "status": status,
            "rejected": rejected,
            "reason_code": tx_sts.get("StsRsnInf", {}).get("Rsn", {}).get("Cd") if rejected else None,
        },
    }


def fednow_liquidity() -> Dict[str, Any]:
    """Generate a FedNow Liquidity Management Transfer (pacs.009.001.08)."""
    ts = rand_ts()
    bank = rand_bank()
    lmt_type = random.choice(["TOP_UP", "DRAWDOWN"])
    amount = rand_amount(1_000_000.00, 100_000_000.00)
    u = uetr()
    lmt_id = msg_id("LMT", ts)
    fedres = {"name": "Federal Reserve Bank", "aba": "021001208", "bic": "FRNYUS33"}

    if lmt_type == "TOP_UP":
        src_acct = f"MASTER-{bank['aba']}"
        dst_acct = f"FEDNOW-BAL-{bank['aba']}"
        src_scheme = "FEDMASTERACCOUNT"
        dst_scheme = "FEDNOWTOPUP"
        purpose = "LMTTOPUP"
    else:
        src_acct = f"FEDNOW-BAL-{bank['aba']}"
        dst_acct = f"MASTER-{bank['aba']}"
        src_scheme = "FEDNOWTOPUP"
        dst_scheme = "FEDMASTERACCOUNT"
        purpose = "LMTDRAWDOWN"

    iso = {
        "AppHdr": {
            "Fr": {"FIId": _fi(bank)},
            "To": {"FIId": {"FinInstnId": {"BICFI": "FRNYUS33", "Nm": "Federal Reserve Bank"}}},
            "BizMsgIdr": lmt_id,
            "MsgDefIdr": "pacs.009.001.08",
            "BizSvc": "fedwire",
            "CreDtTm": iso_ts(ts),
        },
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.009.001.08",
            "FICdtTrf": {
                "GrpHdr": {
                    "MsgId": lmt_id,
                    "CreDtTm": iso_ts(ts),
                    "NbOfTxs": "1",
                    "TtlIntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "IntrBkSttlmDt": biz_date(ts),
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "FDW"}},
                    "InstgAgt": _fi(bank),
                    "InstdAgt": {"FinInstnId": {"BICFI": "FRNYUS33"}},
                },
                "CdtTrfTxInf": {
                    "PmtId": {"InstrId": lmt_id, "EndToEndId": f"LMT-{lmt_type}-{biz_date(ts)}", "UETR": u},
                    "IntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "IntrBkSttlmDt": biz_date(ts),
                    "Dbtr": {"FinInstnId": _fi(bank)["FinInstnId"]},
                    "DbtrAcct": {"Id": {"Othr": {"Id": src_acct, "SchmeNm": {"Prtry": src_scheme}}}},
                    "Cdtr": {"FinInstnId": _fi(bank)["FinInstnId"]},
                    "CdtrAcct": {"Id": {"Othr": {"Id": dst_acct, "SchmeNm": {"Prtry": dst_scheme}}}},
                    "Purp": {"Prtry": purpose},
                    "RmtInf": {"Ustrd": f"FedNow {lmt_type} {biz_date(ts)}"},
                },
            },
        },
    }

    return {
        "_metadata": {"network": "FedNow", "message_type": "pacs.009.001.08 (LMT)", "generated_at": iso_ts(now_utc())},
        "iso20022": iso,
        "flattened": {
            "network": "FedNow",
            "message_type": "Liquidity Management Transfer",
            "lmt_type": lmt_type,
            "lmt_id": lmt_id,
            "uetr": u,
            "amount": float(amount),
            "currency": "USD",
            "bank": bank["name"],
            "source_account": src_acct,
            "destination_account": dst_acct,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  RTP GENERATORS
#  Structurally similar to FedNow — key differences:
#    • pacs.008.001.07 (not .08)
#    • Clearing code TCH (not FDN)
#    • Max amount $1,000,000
#    • Payment status includes ACTC intermediate step
# ═══════════════════════════════════════════════════════════════════════════

def rtp_credit_transfer() -> Dict[str, Any]:
    """Generate an RTP pacs.008.001.07 credit transfer."""
    ts = rand_ts()
    sender_bank = rand_bank()
    receiver_bank = rand_bank(exclude=sender_bank)
    debtor_name = fake.company()
    creditor_name = fake.company()
    debtor_acct = rand_account()
    creditor_acct = rand_account()
    amount = rand_amount(1.00, 999999.00)
    amount_float = float(amount)
    purpose = rand_purpose()
    tx_id = msg_id("RTP", ts)
    instr_id = msg_id(sender_bank["aba"][:4].upper(), ts)
    e2e_id = f"E2E-{fake.bothify('??##-####-???#').upper()}"
    u = uetr()

    iso = {
        "AppHdr": _app_hdr(sender_bank, receiver_bank, msg_id(sender_bank["aba"][:8], ts), "pacs.008.001.07", ts),
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.07",
            "FIToFICstmrCdtTrf": {
                "GrpHdr": {
                    "MsgId": tx_id,
                    "CreDtTm": iso_ts(ts),
                    "NbOfTxs": "1",
                    "TtlIntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "IntrBkSttlmDt": biz_date(ts),
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "TCH"}},
                    "InstgAgt": _fi(sender_bank),
                    "InstdAgt": _fi(receiver_bank),
                },
                "CdtTrfTxInf": {
                    "PmtId": {"InstrId": instr_id, "EndToEndId": e2e_id, "TxId": tx_id, "UETR": u},
                    "IntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "IntrBkSttlmDt": biz_date(ts),
                    "InstdAmt": {"@Ccy": "USD", "#text": amount},
                    "ChrgBr": "SLEV",
                    "PmtTpInf": {"SvcLvl": {"Cd": "URGP"}, "LclInstrm": {"Cd": "RTP"}},
                    "Dbtr": _party_org(debtor_name, rand_tax_id()),
                    "DbtrAcct": _account(debtor_acct),
                    "DbtrAgt": _fi(sender_bank),
                    "CdtrAgt": _fi(receiver_bank),
                    "Cdtr": _party_org(creditor_name, rand_tax_id()),
                    "CdtrAcct": _account(creditor_acct),
                    "Purp": {"Cd": purpose},
                    "RmtInf": {
                        "Ustrd": fake.sentence(nb_words=10),
                        "Strd": {"RfrdDocInf": rand_invoice_refs(1)},
                    },
                },
            },
        },
    }

    flat = {
        "network": "RTP",
        "message_type": "Credit Transfer",
        "message_id": tx_id,
        "created_at": iso_ts(ts),
        "settlement_date": biz_date(ts),
        "settlement_network": "TCH",
        "payment": {
            "instruction_id": instr_id,
            "end_to_end_id": e2e_id,
            "transaction_id": tx_id,
            "uetr": u,
            "amount": amount_float,
            "currency": "USD",
            "purpose_code": purpose,
        },
        "sender_bank": {"name": sender_bank["name"], "routing_number": sender_bank["aba"]},
        "debtor": {"name": debtor_name, "account_number": debtor_acct},
        "receiver_bank": {"name": receiver_bank["name"], "routing_number": receiver_bank["aba"]},
        "creditor": {"name": creditor_name, "account_number": creditor_acct},
    }

    return {
        "_metadata": {"network": "RTP", "message_type": "pacs.008.001.07", "generated_at": iso_ts(now_utc())},
        "iso20022": iso,
        "flattened": flat,
    }


def rtp_payment_status(credit_transfer: Optional[Dict] = None, force_reject: bool = False) -> Dict[str, Any]:
    """Generate an RTP pacs.002.001.10 — includes ACTC intermediate status."""
    ct = credit_transfer or rtp_credit_transfer()
    flat_ct = ct["flattened"]
    orig_ts_str = ct["iso20022"]["AppHdr"]["CreDtTm"]
    orig_dt = datetime.fromisoformat(orig_ts_str.replace("Z", "+00:00"))

    rejected = force_reject or (random.random() < 0.12)
    final_status = "RJCT" if rejected else "ACCP"

    # RTP 3-step: ACTC → ACWP → ACCP
    actc_ts = orig_dt + timedelta(milliseconds=random.randint(200, 800))
    acwp_ts = actc_ts + timedelta(milliseconds=random.randint(3000, 8000))
    accp_ts = acwp_ts + timedelta(milliseconds=random.randint(1000, 5000))

    sender_bank = next(b for b in BANKS if b["aba"] == ct["iso20022"]["AppHdr"]["Fr"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"])
    receiver_bank = next(b for b in BANKS if b["aba"] == ct["iso20022"]["AppHdr"]["To"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"])
    status_msg_id = msg_id("RTPSTS", accp_ts)

    tx_sts: Dict = {
        "StsId": status_msg_id,
        "OrgnlInstrId": flat_ct["payment"]["instruction_id"],
        "OrgnlEndToEndId": flat_ct["payment"]["end_to_end_id"],
        "OrgnlTxId": flat_ct["payment"]["transaction_id"],
        "OrgnlUETR": flat_ct["payment"]["uetr"],
        "TxSts": final_status,
        "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "TCH"}},
    }
    if rejected:
        tx_sts["StsRsnInf"] = {"Rsn": {"Cd": random.choice(RTP_REJECT_CODES)}, "AddtlInf": fake.sentence(nb_words=10)}
    else:
        tx_sts["AccptncDtTm"] = iso_ts(accp_ts)
        tx_sts["FctvIntrBkSttlmDt"] = biz_date(accp_ts)

    total_ms = int((accp_ts - orig_dt).total_seconds() * 1000)

    iso = {
        "AppHdr": _app_hdr(receiver_bank, sender_bank, msg_id(receiver_bank["aba"][:8], accp_ts), "pacs.002.001.10", accp_ts),
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10",
            "FIToFIPmtStsRpt": {
                "GrpHdr": {
                    "MsgId": status_msg_id,
                    "CreDtTm": iso_ts(accp_ts),
                    "InstgAgt": _fi(receiver_bank),
                    "InstdAgt": _fi(sender_bank),
                },
                "OrgnlGrpInfAndSts": {
                    "OrgnlMsgId": ct["iso20022"]["Document"]["FIToFICstmrCdtTrf"]["GrpHdr"]["MsgId"],
                    "OrgnlMsgNmId": "pacs.008.001.07",
                    "GrpSts": final_status,
                },
                "TxInfAndSts": tx_sts,
            },
        },
    }

    return {
        "_metadata": {"network": "RTP", "message_type": "pacs.002.001.10", "generated_at": iso_ts(now_utc())},
        "iso20022": iso,
        "flattened": {
            "network": "RTP",
            "message_type": "Payment Status Report",
            "original_uetr": flat_ct["payment"]["uetr"],
            "final_status": final_status,
            "total_turnaround_ms": total_ms,
            "status_timeline": [
                {"status": "ACTC", "offset_ms": int((actc_ts - orig_dt).total_seconds() * 1000), "description": "TCH technical validation"},
                {"status": "ACWP", "offset_ms": int((acwp_ts - orig_dt).total_seconds() * 1000), "description": "Receiver accepted"},
                {"status": final_status, "offset_ms": total_ms, "description": "Final status"},
            ],
        },
    }


def rtp_return(credit_transfer: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate an RTP pacs.004.001.08 return."""
    ct = credit_transfer or rtp_credit_transfer()
    flat_ct = ct["flattened"]
    orig_ts_str = ct["iso20022"]["AppHdr"]["CreDtTm"]
    orig_settle = ct["iso20022"]["Document"]["FIToFICstmrCdtTrf"]["GrpHdr"]["IntrBkSttlmDt"]
    return_ts = datetime.fromisoformat(orig_ts_str.replace("Z", "+00:00")) + timedelta(days=random.randint(0, 2), hours=random.randint(0, 23))
    reason = random.choice(RETURN_REASON_CODES)
    rtr_id = msg_id("RTPRET", return_ts)
    amount = ct["iso20022"]["Document"]["FIToFICstmrCdtTrf"]["GrpHdr"]["TtlIntrBkSttlmAmt"]["#text"]

    sender_bank = next(b for b in BANKS if b["aba"] == ct["iso20022"]["AppHdr"]["Fr"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"])
    receiver_bank = next(b for b in BANKS if b["aba"] == ct["iso20022"]["AppHdr"]["To"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"])

    iso = {
        "AppHdr": _app_hdr(receiver_bank, sender_bank, msg_id(receiver_bank["aba"][:8], return_ts), "pacs.004.001.08", return_ts),
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.004.001.08",
            "PmtRtr": {
                "GrpHdr": {
                    "MsgId": rtr_id,
                    "CreDtTm": iso_ts(return_ts),
                    "NbOfTxs": "1",
                    "TtlRtrdIntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "IntrBkSttlmDt": biz_date(return_ts),
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "TCH"}},
                    "InstgAgt": _fi(receiver_bank),
                    "InstdAgt": _fi(sender_bank),
                },
                "TxInf": {
                    "RtrId": rtr_id,
                    "OrgnlGrpInf": {
                        "OrgnlMsgId": ct["iso20022"]["Document"]["FIToFICstmrCdtTrf"]["GrpHdr"]["MsgId"],
                        "OrgnlMsgNmId": "pacs.008.001.07",
                    },
                    "OrgnlTxId": flat_ct["payment"]["transaction_id"],
                    "OrgnlUETR": flat_ct["payment"]["uetr"],
                    "OrgnlIntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "OrgnlIntrBkSttlmDt": orig_settle,
                    "RtrdIntrBkSttlmAmt": {"@Ccy": "USD", "#text": amount},
                    "IntrBkSttlmDt": biz_date(return_ts),
                    "RtrRsnInf": {"Rsn": {"Cd": reason}, "AddtlInf": fake.sentence(nb_words=9)},
                },
            },
        },
    }

    return {
        "_metadata": {"network": "RTP", "message_type": "pacs.004.001.08", "generated_at": iso_ts(now_utc())},
        "iso20022": iso,
        "flattened": {
            "network": "RTP",
            "message_type": "Payment Return",
            "return_id": rtr_id,
            "return_amount": float(amount),
            "return_reason_code": reason,
            "original_uetr": flat_ct["payment"]["uetr"],
            "original_settlement_date": orig_settle,
            "return_settlement_date": biz_date(return_ts),
        },
    }


def rtp_rfp() -> Dict[str, Any]:
    """Generate an RTP pain.013.001.06 Request for Payment."""
    ts = rand_ts()
    creditor_bank = rand_bank()
    debtor_bank = rand_bank(exclude=creditor_bank)
    creditor_name = fake.company()
    debtor_name = fake.company()
    creditor_acct = rand_account()
    debtor_acct = rand_account()
    amount = rand_amount(50.00, 500000.00)
    u = uetr()
    rfp_id = msg_id("RTPRFP", ts)
    e2e_id = f"E2E-RFP-{fake.bothify('??##-####').upper()}"

    iso = {
        "AppHdr": _app_hdr(creditor_bank, debtor_bank, msg_id(creditor_bank["aba"][:8], ts), "pain.013.001.06", ts),
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pain.013.001.06",
            "CdtrPmtActvtnReq": {
                "GrpHdr": {
                    "MsgId": rfp_id, "CreDtTm": iso_ts(ts), "NbOfTxs": "1", "CtrlSum": amount,
                    "InitgPty": {"Nm": creditor_bank["name"]},
                },
                "PmtInf": {
                    "PmtInfId": f"{rfp_id}PMT",
                    "PmtMtd": "TRF",
                    "ReqdExctnDt": {"Dt": biz_date(ts + timedelta(days=1))},
                    "XpryDt": {"Dt": biz_date(ts + timedelta(days=2))},
                    "PmtTpInf": {"SvcLvl": {"Cd": "URGP"}, "LclInstrm": {"Cd": "RTP"}},
                    "Dbtr": _party_org(debtor_name, rand_tax_id()),
                    "DbtrAcct": _account(debtor_acct),
                    "DbtrAgt": _fi(debtor_bank),
                    "CdtTrfTxInf": {
                        "PmtId": {"EndToEndId": e2e_id, "UETR": u},
                        "Amt": {"InstdAmt": {"@Ccy": "USD", "#text": amount}},
                        "ChrgBr": "SLEV",
                        "CdtrAgt": _fi(creditor_bank),
                        "Cdtr": _party_org(creditor_name, rand_tax_id()),
                        "CdtrAcct": _account(creditor_acct),
                        "Purp": {"Cd": rand_purpose()},
                        "RmtInf": {"Ustrd": fake.sentence(nb_words=9)},
                    },
                },
            },
        },
    }

    return {
        "_metadata": {"network": "RTP", "message_type": "pain.013.001.06", "generated_at": iso_ts(now_utc())},
        "iso20022": iso,
        "flattened": {
            "network": "RTP", "message_type": "Request for Payment",
            "rfp_id": rfp_id, "uetr": u, "end_to_end_id": e2e_id,
            "amount": float(amount), "currency": "USD",
            "creditor": {"name": creditor_name, "bank": creditor_bank["name"]},
            "debtor": {"name": debtor_name, "bank": debtor_bank["name"]},
        },
    }


def rtp_rfp_response(rfp: Optional[Dict] = None, force_reject: bool = False) -> Dict[str, Any]:
    """Generate an RTP pain.014.001.06 RfP response."""
    rfp_doc = rfp or rtp_rfp()
    ts = rand_ts()
    rejected = force_reject or (random.random() < 0.20)
    status = "RJCT" if rejected else "ACCP"
    rfp_grp_hdr = rfp_doc["iso20022"]["Document"]["CdtrPmtActvtnReq"]["GrpHdr"]
    rfp_pmt_inf = rfp_doc["iso20022"]["Document"]["CdtrPmtActvtnReq"]["PmtInf"]
    flat_rfp = rfp_doc["flattened"]
    debtor_bank_aba = rfp_doc["iso20022"]["AppHdr"]["To"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"]
    creditor_bank_aba = rfp_doc["iso20022"]["AppHdr"]["Fr"]["FIId"]["FinInstnId"]["ClrSysMmbId"]["MmbId"]
    debtor_bank = next(b for b in BANKS if b["aba"] == debtor_bank_aba)
    creditor_bank = next(b for b in BANKS if b["aba"] == creditor_bank_aba)
    resp_id = msg_id("RTPRFPSTS", ts)

    tx_sts: Dict = {
        "StsId": resp_id,
        "OrgnlEndToEndId": flat_rfp["end_to_end_id"],
        "OrgnlUETR": flat_rfp["uetr"],
        "TxSts": status,
    }
    if rejected:
        tx_sts["StsRsnInf"] = {"Rsn": {"Cd": random.choice(["CUST", "AM04", "NOAS"])}, "AddtlInf": fake.sentence(nb_words=7)}
    else:
        tx_sts["AccptncDtTm"] = iso_ts(ts)

    iso = {
        "AppHdr": _app_hdr(debtor_bank, creditor_bank, msg_id(debtor_bank["aba"][:8], ts), "pain.014.001.06", ts),
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pain.014.001.06",
            "CdtrPmtActvtnReqStsRpt": {
                "GrpHdr": {"MsgId": resp_id, "CreDtTm": iso_ts(ts), "InitgPty": {"Nm": debtor_bank["name"]}},
                "OrgnlGrpInfAndSts": {"OrgnlMsgId": rfp_grp_hdr["MsgId"], "OrgnlMsgNmId": "pain.013.001.06", "GrpSts": status},
                "OrgnlPmtInfAndSts": {"OrgnlPmtInfId": rfp_pmt_inf["PmtInfId"], "PmtInfSts": status, "TxInfAndSts": tx_sts},
            },
        },
    }

    return {
        "_metadata": {"network": "RTP", "message_type": "pain.014.001.06", "generated_at": iso_ts(now_utc())},
        "iso20022": iso,
        "flattened": {
            "network": "RTP", "message_type": "RfP Response",
            "response_id": resp_id, "original_rfp_id": rfp_grp_hdr["MsgId"],
            "status": status, "rejected": rejected,
            "reason_code": tx_sts.get("StsRsnInf", {}).get("Rsn", {}).get("Cd") if rejected else None,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  ZELLE GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def _zelle_token(token_type: str) -> str:
    if token_type == "EMAL":
        return fake.email()
    else:
        digits = [str(random.randint(2, 9))] + [str(random.randint(0, 9)) for _ in range(9)]
        return "+1" + "".join(digits)


def zelle_send_payment() -> Dict[str, Any]:
    """Generate a Zelle payment initiation request + response."""
    ts = rand_ts()
    sender_bank = rand_bank()
    sender_name = fake.name()
    recipient_name = fake.name()
    sender_acct = rand_account()
    token_type = random.choice(ZELLE_TOKEN_TYPES)
    token = _zelle_token(token_type)
    amount = rand_amount_float(1.00, 2500.00)
    e2e_id = f"E2E-ZELLE-{ts.strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
    payment_id = f"ZEL{ts.strftime('%Y%m%d')}{sender_bank['aba'][:4]}{random.randint(100000, 999999)}"
    firm_root_id = f"FROOT{sender_bank['aba'][:4]}{ts.strftime('%Y%m%d')}{random.randint(1000, 9999)}"
    zelle_net_id = f"ZNT{ts.strftime('%Y%m%d')}{fake.bothify('######???###').upper()}"
    enrolled = random.random() < 0.80   # 80% chance recipient is enrolled
    status = "COMPLETED" if enrolled else "PENDING"
    complete_ts = ts + timedelta(seconds=random.randint(30, 180))
    memo = random.choice([
        fake.sentence(nb_words=5),
        f"Invoice {fake.bothify('INV-####')}",
        f"Rent {ts.strftime('%B %Y')}",
        f"Split {fake.word()} bill",
        f"Reimbursement for {fake.word()}",
    ])

    req = {
        "_endpoint": "POST /api/v1/payments/zelle",
        "_headers": {"Content-Type": "application/json", "Idempotency-Key": e2e_id},
        "payments": {
            "requestedExecutionDate": biz_date(ts),
            "paymentIdentifiers": {"endToEndId": e2e_id},
            "paymentCurrency": "USD",
            "paymentAmount": amount,
            "transferType": "CREDIT",
            "memo": memo,
            "debtor": {
                "debtorName": sender_name,
                "debtorAccount": {"accountId": sender_acct, "accountType": "CHECKING"},
            },
            "debtorAgent": {
                "financialInstitutionId": {
                    "bic": sender_bank["bic"],
                    "clearingSystemMemberId": {"clearingSystemId": "USABA", "memberId": sender_bank["aba"]},
                }
            },
            "creditor": {
                "creditorName": recipient_name,
                "creditorAccount": {
                    "accountType": "ZELLE",
                    "alternateAccountIdentifier": token,
                    "schemeName": {"proprietary": token_type},
                },
            },
        },
    }

    resp: Dict[str, Any] = {
        "_http_status": 201,
        "payments": {
            "paymentId": payment_id,
            "firmRootId": firm_root_id,
            "endToEndId": e2e_id,
            "createDateTime": iso_ts(ts),
            "paymentStatus": status,
            "paymentAmount": amount,
            "paymentCurrency": "USD",
            "requestedExecutionDate": biz_date(ts),
            "memo": memo,
            "debtor": {"debtorName": sender_name, "debtorAccount": {"accountId": sender_acct}},
            "creditor": {
                "creditorName": recipient_name,
                "creditorAccount": {"alternateAccountIdentifier": token, "schemeName": {"proprietary": token_type}},
            },
            "zelleNetworkTransactionId": zelle_net_id,
            "recipientEnrollmentStatus": "ENROLLED" if enrolled else "NOT_ENROLLED",
        },
    }
    if status == "COMPLETED":
        resp["payments"]["actualSettlementDate"] = biz_date(complete_ts)
        resp["payments"]["lastUpdatedDateTime"] = iso_ts(complete_ts)
    else:
        exp_ts = ts + timedelta(days=14)
        resp["payments"]["paymentExpiryDate"] = biz_date(exp_ts)
        resp["payments"]["paymentStatusDetail"] = f"Recipient {token} is not enrolled. Invitation sent. Expires {biz_date(exp_ts)}."

    return {
        "_metadata": {"network": "Zelle", "message_type": "Payment Initiation", "generated_at": iso_ts(now_utc())},
        "api_request": req,
        "api_response": resp,
        "flattened": {
            "network": "Zelle",
            "message_type": "Send Payment",
            "payment_id": payment_id,
            "end_to_end_id": e2e_id,
            "amount": amount,
            "currency": "USD",
            "memo": memo,
            "status": status,
            "created_at": iso_ts(ts),
            "sender": {"name": sender_name, "account": sender_acct, "bank": sender_bank["name"]},
            "recipient": {"name": recipient_name, "token": token, "token_type": token_type, "enrolled": enrolled},
            "is_reversible": False,
        },
    }


def zelle_payment_status(send_payment: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate a Zelle payment status GET response."""
    sp = send_payment or zelle_send_payment()
    payment_id = sp["api_response"]["payments"]["paymentId"]
    e2e_id = sp["flattened"]["end_to_end_id"]
    original_status = sp["flattened"]["status"]

    # Possibly a rejection scenario (20% of the time we simulate a rejection)
    if random.random() < 0.20:
        status = "REJECTED"
        error_code = random.choice(ZELLE_ERROR_CODES)
    else:
        status = original_status

    ts = rand_ts()
    resp: Dict[str, Any] = {
        "_http_status": 200,
        "payments": {
            "paymentId": payment_id,
            "endToEndId": e2e_id,
            "paymentStatus": status,
            "paymentAmount": sp["flattened"]["amount"],
            "paymentCurrency": "USD",
            "createDateTime": sp["api_response"]["payments"]["createDateTime"],
            "lastUpdatedDateTime": iso_ts(ts),
            "memo": sp["flattened"]["memo"],
        },
    }

    if status == "REJECTED":
        resp["payments"]["exceptions"] = {
            "errorCode": error_code,
            "errorDescription": f"Payment blocked: {error_code.replace('_', ' ').title()}",
            "retryable": error_code in ("SERVICE_UNAVAILABLE",),
        }
    elif status == "COMPLETED":
        resp["payments"]["processingTime"] = {"submitToCompleteMs": random.randint(15000, 180000)}
    elif status == "PENDING":
        exp_date = (ts + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d")
        resp["payments"]["invitationDetails"] = {
            "invitationSentAt": iso_ts(ts),
            "invitationChannel": "EMAIL" if sp["flattened"]["recipient"]["token_type"] == "EMAL" else "SMS",
            "expiresAt": exp_date,
        }

    return {
        "_metadata": {"network": "Zelle", "message_type": "Payment Status", "generated_at": iso_ts(now_utc())},
        "api_request": {"_endpoint": f"GET /api/v1/payments/zelle/{payment_id}"},
        "api_response": resp,
        "flattened": {
            "network": "Zelle",
            "message_type": "Payment Status",
            "payment_id": payment_id,
            "status": status,
            "is_final": status in ("COMPLETED", "REJECTED"),
            "is_reversible": False,
            "error_code": resp["payments"].get("exceptions", {}).get("errorCode"),
        },
    }


def zelle_cancellation(send_payment: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate a Zelle cancellation (only valid for PENDING payments)."""
    sp = send_payment or zelle_send_payment()
    # Force a pending payment for cancellation to make sense
    sp["api_response"]["payments"]["paymentStatus"] = "PENDING"
    sp["flattened"]["status"] = "PENDING"

    payment_id = sp["api_response"]["payments"]["paymentId"]
    ts = rand_ts()
    cancel_success = random.random() < 0.85   # 85% of the time we can cancel

    req = {
        "_endpoint": f"DELETE /api/v1/payments/zelle/{payment_id}",
        "_body": {
            "cancellationReason": random.choice(["CUSTOMER_REQUEST", "PAYMENT_ERROR", "DUPLICATE"]),
            "cancellationNote": fake.sentence(nb_words=8),
        },
    }

    if cancel_success:
        resp: Dict[str, Any] = {
            "_http_status": 200,
            "payments": {
                "paymentId": payment_id,
                "endToEndId": sp["flattened"]["end_to_end_id"],
                "paymentStatus": "CANCELLED",
                "cancelledAt": iso_ts(ts),
                "cancellationReason": req["_body"]["cancellationReason"],
                "refundNote": "Payment was PENDING — sender account was not debited. No refund required.",
                "originalPaymentAmount": sp["flattened"]["amount"],
            },
        }
    else:
        resp = {
            "_http_status": 409,
            "error": {
                "errorCode": "CANCELLATION_NOT_PERMITTED",
                "errorDescription": "Payment is COMPLETED and cannot be cancelled. File a dispute with your bank if fraud is suspected.",
                "paymentStatus": "COMPLETED",
                "regulatoryReference": "Regulation E (12 CFR 1005)",
            },
        }

    return {
        "_metadata": {"network": "Zelle", "message_type": "Cancellation", "generated_at": iso_ts(now_utc())},
        "api_request": req,
        "api_response": resp,
        "flattened": {
            "network": "Zelle",
            "message_type": "Cancellation",
            "payment_id": payment_id,
            "cancellation_success": cancel_success,
            "final_status": "CANCELLED" if cancel_success else "COMPLETED (not reversible)",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  GENERATOR REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

GENERATORS = {
    "fednow": {
        "credit_transfer": fednow_credit_transfer,
        "payment_status":  fednow_payment_status,
        "return":          fednow_return,
        "rfp":             fednow_rfp,
        "rfp_response":    fednow_rfp_response,
        "liquidity":       fednow_liquidity,
    },
    "rtp": {
        "credit_transfer": rtp_credit_transfer,
        "payment_status":  rtp_payment_status,
        "return":          rtp_return,
        "rfp":             rtp_rfp,
        "rfp_response":    rtp_rfp_response,
    },
    "zelle": {
        "send_payment":   zelle_send_payment,
        "payment_status": zelle_payment_status,
        "cancellation":   zelle_cancellation,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  OUTPUT WRITERS
# ═══════════════════════════════════════════════════════════════════════════

def write_json_array(records: List[Dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def write_jsonl(records: List[Dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic payment messages for Zelle, FedNow, and RTP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--network", choices=["fednow", "rtp", "zelle", "all"], default="all",
                        help="Payment network to generate for (default: all)")
    parser.add_argument("--type", dest="msg_type", default="all",
                        help="Message type (e.g. credit_transfer, payment_status, return, rfp, rfp_response, liquidity). Default: all")
    parser.add_argument("--count", type=int, default=10,
                        help="Number of records per message type (default: 10)")
    parser.add_argument("--output-dir", default="generated_payments",
                        help="Output directory (default: generated_payments)")
    parser.add_argument("--format", choices=["json", "jsonl"], default="json",
                        help="Output format: json (array) or jsonl (one record per line). Default: json")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible output (default: random)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print one sample of each type to stdout instead of writing files")
    args = parser.parse_args()

    if args.seed is not None:
        Faker.seed(args.seed)
        random.seed(args.seed)

    os.makedirs(args.output_dir, exist_ok=True)

    networks = list(GENERATORS.keys()) if args.network == "all" else [args.network]
    ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    total_written = 0

    for network in networks:
        net_generators = GENERATORS[network]
        types = list(net_generators.keys()) if args.msg_type == "all" else [args.msg_type]

        for msg_type in types:
            if msg_type not in net_generators:
                print(f"  ⚠  Unknown type '{msg_type}' for network '{network}'. Skipping.")
                continue

            gen_fn = net_generators[msg_type]
            print(f"  Generating {args.count:,} × {network}/{msg_type}...", end=" ", flush=True)
            records = []
            for _ in range(args.count):
                try:
                    records.append(gen_fn())
                except Exception as e:
                    print(f"\n    ⚠ Error: {e}")
                    continue

            if args.dry_run:
                print()
                print(json.dumps(records[0], indent=2, ensure_ascii=False)[:2000])
                print("  ... (truncated to 2000 chars for dry-run)")
                continue

            ext = "jsonl" if args.format == "jsonl" else "json"
            filename = f"{network}_{msg_type}_{ts_tag}.{ext}"
            filepath = os.path.join(args.output_dir, filename)

            if args.format == "jsonl":
                write_jsonl(records, filepath)
            else:
                write_json_array(records, filepath)

            total_written += len(records)
            print(f"→  {filepath}")

    if not args.dry_run:
        print(f"\n  ✓ Done. {total_written:,} records written to: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
