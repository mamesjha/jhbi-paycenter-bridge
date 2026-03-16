#!/usr/bin/env python3
"""
=============================================================================
  Payment Format Sample Library
  Zelle  |  FedNow  |  RTP (The Clearing House)
=============================================================================

CONTENTS
--------
All sample messages are exposed as Python dicts (importable as constants).
Run this script directly to regenerate all JSON files from these constants.

  FEDNOW_CREDIT_TRANSFER       pacs.008.001.08   Credit transfer
  FEDNOW_PAYMENT_STATUS        pacs.002.001.10   Acceptance / rejection
  FEDNOW_RETURN                pacs.004.001.09   Payment return
  FEDNOW_RFP                   pain.013.001.07   Request for Payment
  FEDNOW_RFP_RESPONSE          pain.014.001.07   RfP accept / reject
  FEDNOW_LIQUIDITY             pacs.009.001.08   Liquidity Management Transfer

  RTP_CREDIT_TRANSFER          pacs.008.001.07   Credit transfer
  RTP_PAYMENT_STATUS           pacs.002.001.10   Status report (inc. ACTC)
  RTP_RETURN                   pacs.004.001.08   Payment return
  RTP_RFP                      pain.013.001.06   Request for Payment
  RTP_RFP_RESPONSE             pain.014.001.06   RfP response

  ZELLE_SEND_PAYMENT           REST POST         Payment send
  ZELLE_PAYMENT_STATUS         REST GET          Status inquiry
  ZELLE_RETURN_CANCELLATION    REST DELETE       Cancel / return

USAGE
-----
  # Import and use in tests:
  from payment_samples import FEDNOW_CREDIT_TRANSFER, RTP_PAYMENT_STATUS

  # Access ISO 20022 layer:
  uetr = FEDNOW_CREDIT_TRANSFER["iso20022"]["Document"]["FIToFICstmrCdtTrf"]\
             ["CdtTrfTxInf"]["PmtId"]["UETR"]

  # Access flattened layer:
  amount = FEDNOW_CREDIT_TRANSFER["flattened"]["payment"]["amount"]

  # Generate all JSON files:
  python payment_samples.py

  # Write to a specific directory:
  python payment_samples.py --output-dir /path/to/my/samples

KEY DIFFERENCES CHEAT SHEET
----------------------------
  Feature                FedNow                RTP (TCH)             Zelle (EWS)
  ─────────────────────  ────────────────────  ────────────────────  ───────────────────────
  ISO 20022 version      pacs.008.001.08       pacs.008.001.07       Not ISO 20022 natively
  Clearing code          FDN                   TCH                   N/A (ACH-based)
  Max amount             $500,000              $1,000,000            Bank-set ($500–$2,500/day)
  Settlement speed       < 20 seconds          < 15 seconds          1–3 minutes (enrolled)
  Response window        20 sec (ACCP/RJCT)    15 sec (ACCP/RJCT)   Async callback
  Status: ACK            ACCP                  ACTC → ACWP → ACCP   COMPLETED
  Request for Payment    pain.013 ✓            pain.013 ✓            ✗ Not supported
  Reversals              pacs.004 ✓            pacs.004 ✓            ✗ Not supported (COMPLETED)
  Recipient ID           Routing + Account     Routing + Account     Email or Phone (token)
  Operator               Federal Reserve       The Clearing House    Early Warning Services
  Operating hours        24 x 7 x 365          24 x 7 x 365          24 x 7 x 365
=============================================================================
"""

import argparse
import json
import os
import sys
from typing import Dict, Any

# ═══════════════════════════════════════════════════════════════════════════
#  SHARED TEST DATA
#  Consistent parties reused across all message types for easy cross-referencing
# ═══════════════════════════════════════════════════════════════════════════

_JPMC_ABA    = "021000021"
_BOA_ABA     = "021000089"
_CITI_ABA    = "026009593"
_WFB_ABA     = "122000247"

_UETR_FDN    = "3d9f1c7a-2b4e-4f8a-9c1d-6e7f0a2b3c4d"   # FedNow scenario
_UETR_RTP    = "f1e2d3c4-b5a6-7f8e-9d0c-b1a2c3d4e5f6"   # RTP scenario
_UETR_RFP_F  = "9b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e"   # FedNow RfP
_UETR_RFP_R  = "c2d3e4f5-a6b7-8c9d-0e1f-2a3b4c5d6e7f"   # RTP RfP
_UETR_LMT    = "a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6"   # Liquidity

# ═══════════════════════════════════════════════════════════════════════════
#  FEDNOW — pacs.008.001.08  CREDIT TRANSFER
# ═══════════════════════════════════════════════════════════════════════════

FEDNOW_CREDIT_TRANSFER: Dict[str, Any] = {
    "_metadata": {
        "network": "FedNow",
        "message_type": "pacs.008.001.08",
        "description": "FI to FI Customer Credit Transfer",
        "settlement_code": "FDN",
        "max_amount_usd": 500000,
        "notes": [
            "UETR is mandatory — UUID v4",
            "ChrgBr SLEV = Service Level (bearer per agreement)",
            "FedNow settles USD only, 24x7x365",
            "MmbId = 9-digit ABA routing number"
        ]
    },
    "iso20022": {
        "AppHdr": {
            "Fr": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}, "Nm": "JPMorgan Chase Bank, N.A."}}},
            "To": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _BOA_ABA}, "Nm": "Bank of America, N.A."}}},
            "BizMsgIdr": "20250315JPMC0000000123",
            "MsgDefIdr": "pacs.008.001.08",
            "BizSvc": "iso20022:xsd$pacs.008.001.08",
            "CreDtTm": "2025-03-15T14:23:45.123Z",
            "PssblDplct": False
        },
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08",
            "FIToFICstmrCdtTrf": {
                "GrpHdr": {
                    "MsgId": "FEDNOW20250315JPMC0000000123",
                    "CreDtTm": "2025-03-15T14:23:45.123Z",
                    "NbOfTxs": "1",
                    "TtlIntrBkSttlmAmt": {"@Ccy": "USD", "#text": "47500.00"},
                    "IntrBkSttlmDt": "2025-03-15",
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "FDN"}},
                    "InstgAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}}},
                    "InstdAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _BOA_ABA}}}
                },
                "CdtTrfTxInf": {
                    "PmtId": {
                        "InstrId": "JPMC20250315INS0000123",
                        "EndToEndId": "E2E-PAYROLL-MARCH-2025-0001",
                        "TxId": "FEDNOW20250315TXN000000123",
                        "UETR": _UETR_FDN
                    },
                    "IntrBkSttlmAmt": {"@Ccy": "USD", "#text": "47500.00"},
                    "IntrBkSttlmDt": "2025-03-15",
                    "InstdAmt": {"@Ccy": "USD", "#text": "47500.00"},
                    "ChrgBr": "SLEV",
                    "Dbtr": {
                        "Nm": "Meridian Healthcare Corp",
                        "PstlAdr": {"StrtNm": "1200 Financial Drive Suite 400", "TwnNm": "New York", "CtrySubDvsn": "NY", "PstCd": "10022", "Ctry": "US"},
                        "Id": {"OrgId": {"AnyBIC": "MDHCUS33", "Othr": {"Id": "47-3921845", "SchmeNm": {"Cd": "TXID"}}}}
                    },
                    "DbtrAcct": {"Id": {"Othr": {"Id": "4532109876543210", "SchmeNm": {"Cd": "BBAN"}}}, "Tp": {"Cd": "CACC"}, "Ccy": "USD"},
                    "DbtrAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}, "Nm": "JPMorgan Chase Bank, N.A."}},
                    "CdtrAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _BOA_ABA}, "Nm": "Bank of America, N.A."}},
                    "Cdtr": {
                        "Nm": "Apex Medical Suppliers LLC",
                        "PstlAdr": {"StrtNm": "7800 Supply Chain Boulevard", "TwnNm": "Charlotte", "CtrySubDvsn": "NC", "PstCd": "28201", "Ctry": "US"},
                        "Id": {"OrgId": {"Othr": {"Id": "82-4416790", "SchmeNm": {"Cd": "TXID"}}}}
                    },
                    "CdtrAcct": {"Id": {"Othr": {"Id": "8821097654321098", "SchmeNm": {"Cd": "BBAN"}}}, "Tp": {"Cd": "CACC"}, "Ccy": "USD"},
                    "Purp": {"Cd": "SUPP"},
                    "RmtInf": {
                        "Ustrd": "Payment for INV-2025-0892 and INV-2025-0901 - Medical supply order Q1 2025",
                        "Strd": {"RfrdDocInf": [{"Tp": {"CdOrPrtry": {"Cd": "CINV"}}, "Nb": "INV-2025-0892", "RltdDt": "2025-03-01"}, {"Tp": {"CdOrPrtry": {"Cd": "CINV"}}, "Nb": "INV-2025-0901", "RltdDt": "2025-03-08"}]}
                    }
                }
            }
        }
    },
    "flattened": {
        "network": "FedNow",
        "message_type": "Credit Transfer",
        "message_id": "FEDNOW20250315JPMC0000000123",
        "created_at": "2025-03-15T14:23:45.123Z",
        "settlement_date": "2025-03-15",
        "settlement_network": "FDN",
        "payment": {
            "instruction_id": "JPMC20250315INS0000123",
            "end_to_end_id": "E2E-PAYROLL-MARCH-2025-0001",
            "transaction_id": "FEDNOW20250315TXN000000123",
            "uetr": _UETR_FDN,
            "amount": 47500.00,
            "currency": "USD",
            "purpose_code": "SUPP",
            "remittance_info": "Payment for INV-2025-0892 and INV-2025-0901"
        },
        "sender_bank": {"name": "JPMorgan Chase Bank, N.A.", "routing_number": _JPMC_ABA},
        "debtor": {"name": "Meridian Healthcare Corp", "account_number": "4532109876543210", "account_type": "CACC"},
        "receiver_bank": {"name": "Bank of America, N.A.", "routing_number": _BOA_ABA},
        "creditor": {"name": "Apex Medical Suppliers LLC", "account_number": "8821097654321098", "account_type": "CACC"}
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  FEDNOW — pacs.002.001.10  PAYMENT STATUS
# ═══════════════════════════════════════════════════════════════════════════

FEDNOW_PAYMENT_STATUS: Dict[str, Any] = {
    "_metadata": {
        "network": "FedNow",
        "message_type": "pacs.002.001.10",
        "description": "Payment Status Report",
        "status_codes": {"ACCP": "Accepted and posted", "ACWP": "Accepted without posting", "PDNG": "Pending", "RJCT": "Rejected"},
        "common_reject_codes": {"AC01": "Bad account", "AC04": "Closed account", "AM04": "Insufficient funds", "AM05": "Duplicate", "NARR": "Free text"}
    },
    "iso20022": {
        "AppHdr": {
            "Fr": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _BOA_ABA}}}},
            "To": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}}}},
            "BizMsgIdr": "20250315BOA0000000456",
            "MsgDefIdr": "pacs.002.001.10",
            "BizSvc": "iso20022:xsd$pacs.002.001.10",
            "CreDtTm": "2025-03-15T14:23:46.892Z"
        },
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10",
            "FIToFIPmtStsRpt": {
                "GrpHdr": {
                    "MsgId": "STATUSRPT20250315BOA0000000456",
                    "CreDtTm": "2025-03-15T14:23:46.892Z",
                    "InstgAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _BOA_ABA}}},
                    "InstdAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}}}
                },
                "OrgnlGrpInfAndSts": {
                    "OrgnlMsgId": "FEDNOW20250315JPMC0000000123",
                    "OrgnlMsgNmId": "pacs.008.001.08",
                    "OrgnlCreDtTm": "2025-03-15T14:23:45.123Z",
                    "OrgnlNbOfTxs": "1",
                    "GrpSts": "ACCP"
                },
                "TxInfAndSts": {
                    "StsId": "STSR20250315BOA0000000456",
                    "OrgnlInstrId": "JPMC20250315INS0000123",
                    "OrgnlEndToEndId": "E2E-PAYROLL-MARCH-2025-0001",
                    "OrgnlTxId": "FEDNOW20250315TXN000000123",
                    "OrgnlUETR": _UETR_FDN,
                    "TxSts": "ACCP",
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "FDN"}},
                    "AccptncDtTm": "2025-03-15T14:23:46.731Z",
                    "FctvIntrBkSttlmDt": "2025-03-15"
                }
            }
        }
    },
    "iso20022_rejection_example": {
        "TxInfAndSts": {
            "OrgnlUETR": "8a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
            "TxSts": "RJCT",
            "StsRsnInf": {
                "Rsn": {"Cd": "AC04"},
                "AddtlInf": "Creditor account closed. Verify beneficiary details."
            }
        }
    },
    "flattened": {
        "network": "FedNow",
        "message_type": "Payment Status Report",
        "original_uetr": _UETR_FDN,
        "status": "ACCP",
        "accepted_at": "2025-03-15T14:23:46.731Z",
        "turnaround_ms": 1608,
        "is_final": True,
        "rejection_example": {"status": "RJCT", "reason_code": "AC04", "description": "Closed account number"}
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  FEDNOW — pacs.004.001.09  PAYMENT RETURN
# ═══════════════════════════════════════════════════════════════════════════

FEDNOW_RETURN: Dict[str, Any] = {
    "_metadata": {
        "network": "FedNow",
        "message_type": "pacs.004.001.09",
        "description": "Payment Return — full return of a settled credit transfer",
        "return_window": "2 business days from original settlement",
        "partial_returns": "NOT supported via pacs.004 — use a new pacs.008 for partial",
        "common_return_codes": {
            "AC04": "Closed account", "CUST": "Customer request",
            "DUPL": "Duplicate", "MD06": "End-customer refund request",
            "AM09": "Wrong amount", "NARR": "Narrative"
        }
    },
    "iso20022": {
        "AppHdr": {
            "Fr": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _BOA_ABA}}}},
            "To": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}}}},
            "BizMsgIdr": "20250316BOA0000000789",
            "MsgDefIdr": "pacs.004.001.09",
            "CreDtTm": "2025-03-16T09:15:22.445Z"
        },
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.004.001.09",
            "PmtRtr": {
                "GrpHdr": {
                    "MsgId": "RETURN20250316BOA0000000789",
                    "CreDtTm": "2025-03-16T09:15:22.445Z",
                    "NbOfTxs": "1",
                    "TtlRtrdIntrBkSttlmAmt": {"@Ccy": "USD", "#text": "47500.00"},
                    "IntrBkSttlmDt": "2025-03-16",
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "FDN"}},
                    "InstgAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _BOA_ABA}}},
                    "InstdAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}}}
                },
                "TxInf": {
                    "RtrId": "RTR20250316BOA0000000789",
                    "OrgnlGrpInf": {"OrgnlMsgId": "FEDNOW20250315JPMC0000000123", "OrgnlMsgNmId": "pacs.008.001.08"},
                    "OrgnlInstrId": "JPMC20250315INS0000123",
                    "OrgnlEndToEndId": "E2E-PAYROLL-MARCH-2025-0001",
                    "OrgnlTxId": "FEDNOW20250315TXN000000123",
                    "OrgnlUETR": _UETR_FDN,
                    "RtrdIntrBkSttlmAmt": {"@Ccy": "USD", "#text": "47500.00"},
                    "IntrBkSttlmDt": "2025-03-16",
                    "RtrRsnInf": {
                        "Rsn": {"Cd": "CUST"},
                        "AddtlInf": "Creditor requests return — goods order INV-2025-0892 cancelled per mutual agreement."
                    }
                }
            }
        }
    },
    "flattened": {
        "network": "FedNow",
        "message_type": "Payment Return",
        "return_id": "RTR20250316BOA0000000789",
        "return_amount": 47500.00,
        "return_currency": "USD",
        "return_reason_code": "CUST",
        "original_uetr": _UETR_FDN,
        "original_settlement_date": "2025-03-15",
        "return_settlement_date": "2025-03-16"
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  FEDNOW — pain.013.001.07  REQUEST FOR PAYMENT
# ═══════════════════════════════════════════════════════════════════════════

FEDNOW_RFP: Dict[str, Any] = {
    "_metadata": {
        "network": "FedNow",
        "message_type": "pain.013.001.07",
        "description": "Request for Payment — creditor requests funds from debtor via FedNow RfP",
        "notes": [
            "Does NOT move money — requests that the debtor initiate a pacs.008",
            "Debtor bank presents RfP to customer for approval or rejection",
            "Resulting pacs.008 must use same EndToEndId as this pain.013"
        ]
    },
    "iso20022": {
        "AppHdr": {
            "Fr": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _BOA_ABA}}}},
            "To": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}}}},
            "BizMsgIdr": "20250315BOA0000RFP001",
            "MsgDefIdr": "pain.013.001.07",
            "CreDtTm": "2025-03-15T09:00:00.000Z"
        },
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pain.013.001.07",
            "CdtrPmtActvtnReq": {
                "GrpHdr": {
                    "MsgId": "RFP20250315BOA0000001",
                    "CreDtTm": "2025-03-15T09:00:00.000Z",
                    "NbOfTxs": "1",
                    "CtrlSum": "47500.00",
                    "InitgPty": {"Nm": "Bank of America, N.A.", "Id": {"OrgId": {"AnyBIC": "BOFAUS3N"}}}
                },
                "PmtInf": {
                    "PmtInfId": "PMTINF20250315BOA0000001",
                    "PmtMtd": "TRF",
                    "ReqdExctnDt": {"Dt": "2025-03-15"},
                    "XpryDt": {"Dt": "2025-03-17"},
                    "PmtTpInf": {"SvcLvl": {"Cd": "URGP"}, "LclInstrm": {"Prtry": "FEDNOW"}, "CtgyPurp": {"Cd": "SUPP"}},
                    "Dbtr": {
                        "Nm": "Meridian Healthcare Corp",
                        "Id": {"OrgId": {"Othr": {"Id": "47-3921845", "SchmeNm": {"Cd": "TXID"}}}}
                    },
                    "DbtrAcct": {"Id": {"Othr": {"Id": "4532109876543210", "SchmeNm": {"Cd": "BBAN"}}}},
                    "DbtrAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}}},
                    "CdtTrfTxInf": {
                        "PmtId": {"InstrId": "BOA20250315RFP0000001", "EndToEndId": "E2E-RFP-INV0892-2025", "UETR": _UETR_RFP_F},
                        "Amt": {"InstdAmt": {"@Ccy": "USD", "#text": "47500.00"}},
                        "ChrgBr": "SLEV",
                        "CdtrAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _BOA_ABA}}},
                        "Cdtr": {"Nm": "Apex Medical Suppliers LLC"},
                        "CdtrAcct": {"Id": {"Othr": {"Id": "8821097654321098", "SchmeNm": {"Cd": "BBAN"}}}},
                        "Purp": {"Cd": "SUPP"},
                        "RmtInf": {"Ustrd": "Payment request for INV-2025-0892 and INV-2025-0901 due 2025-03-15"}
                    }
                }
            }
        }
    },
    "flattened": {
        "network": "FedNow",
        "message_type": "Request for Payment",
        "rfp_id": "RFP20250315BOA0000001",
        "uetr": _UETR_RFP_F,
        "end_to_end_id": "E2E-RFP-INV0892-2025",
        "requested_execution_date": "2025-03-15",
        "expiry_date": "2025-03-17",
        "amount": 47500.00,
        "currency": "USD",
        "creditor": {"name": "Apex Medical Suppliers LLC", "bank_routing": _BOA_ABA},
        "debtor": {"name": "Meridian Healthcare Corp", "bank_routing": _JPMC_ABA}
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  FEDNOW — pain.014.001.07  RFP RESPONSE
# ═══════════════════════════════════════════════════════════════════════════

FEDNOW_RFP_RESPONSE: Dict[str, Any] = {
    "_metadata": {
        "network": "FedNow",
        "message_type": "pain.014.001.07",
        "description": "RfP Status Report — ACCP triggers a pacs.008; RJCT terminates the RfP"
    },
    "iso20022_acceptance": {
        "AppHdr": {
            "Fr": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"MmbId": _JPMC_ABA}}}},
            "To": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"MmbId": _BOA_ABA}}}},
            "MsgDefIdr": "pain.014.001.07",
            "CreDtTm": "2025-03-15T11:45:30.000Z"
        },
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pain.014.001.07",
            "CdtrPmtActvtnReqStsRpt": {
                "GrpHdr": {"MsgId": "RFPSTS20250315JPMC0000001", "CreDtTm": "2025-03-15T11:45:30.000Z", "InitgPty": {"Nm": "JPMorgan Chase Bank, N.A."}},
                "OrgnlGrpInfAndSts": {"OrgnlMsgId": "RFP20250315BOA0000001", "OrgnlMsgNmId": "pain.013.001.07", "GrpSts": "ACCP"},
                "OrgnlPmtInfAndSts": {
                    "OrgnlPmtInfId": "PMTINF20250315BOA0000001",
                    "PmtInfSts": "ACCP",
                    "TxInfAndSts": {
                        "OrgnlEndToEndId": "E2E-RFP-INV0892-2025",
                        "OrgnlUETR": _UETR_RFP_F,
                        "TxSts": "ACCP",
                        "AccptncDtTm": "2025-03-15T11:45:28.000Z"
                    }
                }
            }
        }
    },
    "iso20022_rejection": {
        "TxInfAndSts": {
            "TxSts": "RJCT",
            "StsRsnInf": {"Rsn": {"Cd": "CUST"}, "AddtlInf": "Customer disputes invoice amounts."}
        }
    },
    "flattened": {
        "network": "FedNow",
        "message_type": "RfP Response",
        "acceptance": {"status": "ACCP", "accepted_at": "2025-03-15T11:45:28.000Z", "note": "pacs.008 will follow"},
        "rejection": {"status": "RJCT", "reason_code": "CUST", "description": "Customer request — dispute"}
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  FEDNOW — pacs.009.001.08  LIQUIDITY MANAGEMENT TRANSFER
# ═══════════════════════════════════════════════════════════════════════════

FEDNOW_LIQUIDITY: Dict[str, Any] = {
    "_metadata": {
        "network": "FedNow / Fedwire",
        "message_type": "pacs.009.001.08 (Liquidity Management Transfer)",
        "description": "Moves funds between a bank's Fed Master Account and its FedNow Prefunded Balance",
        "settlement_mechanism": "Fedwire Funds Service (FDW)",
        "lmt_types": {"TOP_UP": "Master Account → FedNow Balance", "DRAWDOWN": "FedNow Balance → Master Account"},
        "notes": [
            "FedNow requires a Prefunded Balance — must be ≥ 0 at all times",
            "Payments are rejected if Prefunded Balance is insufficient",
            "LMTs settled via Fedwire (FDW), not FedNow clearing (FDN)"
        ]
    },
    "iso20022": {
        "AppHdr": {
            "Fr": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}, "Nm": "JPMorgan Chase Bank, N.A."}}},
            "To": {"FIId": {"FinInstnId": {"BICFI": "FRNYUS33", "Nm": "Federal Reserve Bank of New York"}}},
            "BizMsgIdr": "20250315JPMC0000LMT001",
            "MsgDefIdr": "pacs.009.001.08",
            "BizSvc": "fedwire",
            "CreDtTm": "2025-03-15T07:30:00.000Z"
        },
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.009.001.08",
            "FICdtTrf": {
                "GrpHdr": {
                    "MsgId": "LMT20250315JPMC0000001",
                    "CreDtTm": "2025-03-15T07:30:00.000Z",
                    "NbOfTxs": "1",
                    "TtlIntrBkSttlmAmt": {"@Ccy": "USD", "#text": "25000000.00"},
                    "IntrBkSttlmDt": "2025-03-15",
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "FDW"}},
                    "InstgAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}}},
                    "InstdAgt": {"FinInstnId": {"BICFI": "FRNYUS33"}}
                },
                "CdtTrfTxInf": {
                    "PmtId": {"InstrId": "JPMC20250315LMT0000001", "EndToEndId": "LMT-TOPUP-20250315-001", "TxId": "FEDWIRELMT20250315001", "UETR": _UETR_LMT},
                    "IntrBkSttlmAmt": {"@Ccy": "USD", "#text": "25000000.00"},
                    "IntrBkSttlmDt": "2025-03-15",
                    "Dbtr": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}}},
                    "DbtrAcct": {"Id": {"Othr": {"Id": "MASTER-ACCOUNT-JPMC", "SchmeNm": {"Prtry": "FEDMASTERACCOUNT"}}}},
                    "Cdtr": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _JPMC_ABA}}},
                    "CdtrAcct": {"Id": {"Othr": {"Id": "FEDNOW-PREFUNDED-BAL-JPMC", "SchmeNm": {"Prtry": "FEDNOWTOPUP"}}}},
                    "Purp": {"Prtry": "LMTTOPUP"},
                    "RmtInf": {"Ustrd": "FedNow Prefunded Balance Top-Up 2025-03-15"}
                }
            }
        }
    },
    "flattened": {
        "network": "FedNow / Fedwire",
        "message_type": "Liquidity Management Transfer",
        "lmt_type": "TOP_UP",
        "amount": 25000000.00,
        "currency": "USD",
        "uetr": _UETR_LMT,
        "source": {"account_type": "Fed Master Account", "bank": "JPMorgan Chase Bank, N.A."},
        "destination": {"account_type": "FedNow Prefunded Balance", "bank": "JPMorgan Chase Bank, N.A."}
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  RTP — pacs.008.001.07  CREDIT TRANSFER
# ═══════════════════════════════════════════════════════════════════════════

RTP_CREDIT_TRANSFER: Dict[str, Any] = {
    "_metadata": {
        "network": "RTP (The Clearing House)",
        "message_type": "pacs.008.001.07",
        "description": "FI to FI Customer Credit Transfer via TCH RTP",
        "settlement_code": "TCH",
        "max_amount_usd": 1000000,
        "key_differences_from_fednow": {
            "message_version": "pacs.008.001.07 (RTP) vs .001.08 (FedNow)",
            "clearing_code": "TCH vs FDN",
            "max_amount": "$1M (RTP) vs $500K (FedNow)",
            "status_flow": "RTP: ACTC → ACWP → ACCP | FedNow: directly ACCP"
        }
    },
    "iso20022": {
        "AppHdr": {
            "Fr": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _CITI_ABA}, "Nm": "Citibank, N.A."}}},
            "To": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _WFB_ABA}, "Nm": "Wells Fargo Bank, N.A."}}},
            "BizMsgIdr": "20250315CITI0000000555",
            "MsgDefIdr": "pacs.008.001.07",
            "BizSvc": "iso20022:xsd$pacs.008.001.07",
            "CreDtTm": "2025-03-15T18:05:33.721Z"
        },
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.07",
            "FIToFICstmrCdtTrf": {
                "GrpHdr": {
                    "MsgId": "RTP20250315CITI0000000555",
                    "CreDtTm": "2025-03-15T18:05:33.721Z",
                    "NbOfTxs": "1",
                    "TtlIntrBkSttlmAmt": {"@Ccy": "USD", "#text": "3850.75"},
                    "IntrBkSttlmDt": "2025-03-15",
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "TCH"}},
                    "InstgAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _CITI_ABA}}},
                    "InstdAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _WFB_ABA}}}
                },
                "CdtTrfTxInf": {
                    "PmtId": {"InstrId": "CITI20250315INS0000555", "EndToEndId": "E2E-INVOICE-WFB-2025-0315", "TxId": "RTP20250315TXN000000555", "UETR": _UETR_RTP},
                    "IntrBkSttlmAmt": {"@Ccy": "USD", "#text": "3850.75"},
                    "IntrBkSttlmDt": "2025-03-15",
                    "InstdAmt": {"@Ccy": "USD", "#text": "3850.75"},
                    "ChrgBr": "SLEV",
                    "PmtTpInf": {"SvcLvl": {"Cd": "URGP"}, "LclInstrm": {"Cd": "RTP"}},
                    "Dbtr": {"Nm": "GlobalTech Solutions Inc", "PstlAdr": {"TwnNm": "New York", "CtrySubDvsn": "NY", "Ctry": "US"}},
                    "DbtrAcct": {"Id": {"Othr": {"Id": "7654321098765432", "SchmeNm": {"Cd": "BBAN"}}}, "Tp": {"Cd": "CACC"}},
                    "DbtrAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _CITI_ABA}}},
                    "CdtrAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _WFB_ABA}}},
                    "Cdtr": {"Nm": "Pacific Coast Consulting LLC", "PstlAdr": {"TwnNm": "San Francisco", "CtrySubDvsn": "CA", "Ctry": "US"}},
                    "CdtrAcct": {"Id": {"Othr": {"Id": "1122334455667788", "SchmeNm": {"Cd": "BBAN"}}}, "Tp": {"Cd": "CACC"}},
                    "Purp": {"Cd": "BEXP"},
                    "RmtInf": {"Ustrd": "Consulting services March 2025 — PCC-INV-2025-0115"}
                }
            }
        }
    },
    "flattened": {
        "network": "RTP",
        "message_type": "Credit Transfer",
        "message_id": "RTP20250315CITI0000000555",
        "settlement_network": "TCH",
        "payment": {"uetr": _UETR_RTP, "amount": 3850.75, "currency": "USD", "purpose_code": "BEXP"},
        "sender_bank": {"name": "Citibank, N.A.", "routing_number": _CITI_ABA},
        "debtor": {"name": "GlobalTech Solutions Inc", "account_number": "7654321098765432"},
        "receiver_bank": {"name": "Wells Fargo Bank, N.A.", "routing_number": _WFB_ABA},
        "creditor": {"name": "Pacific Coast Consulting LLC", "account_number": "1122334455667788"}
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  RTP — pacs.002.001.10  PAYMENT STATUS  (inc. ACTC intermediate)
# ═══════════════════════════════════════════════════════════════════════════

RTP_PAYMENT_STATUS: Dict[str, Any] = {
    "_metadata": {
        "network": "RTP (The Clearing House)",
        "message_type": "pacs.002.001.10",
        "description": "Payment Status Report — RTP 3-step lifecycle: ACTC → ACWP → ACCP",
        "status_lifecycle": ["ACTC (TCH validation)", "ACWP (receiver accepted)", "ACCP (funds posted)"],
        "rtp_vs_fednow": "RTP uses ACTC as an intermediate; FedNow goes directly to ACCP"
    },
    "iso20022_final_accp": {
        "AppHdr": {
            "Fr": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"MmbId": _WFB_ABA}}}},
            "To": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"MmbId": _CITI_ABA}}}},
            "MsgDefIdr": "pacs.002.001.10",
            "CreDtTm": "2025-03-15T18:05:46.092Z"
        },
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10",
            "FIToFIPmtStsRpt": {
                "GrpHdr": {"MsgId": "RTPSTATUS20250315WFB0000001", "CreDtTm": "2025-03-15T18:05:46.092Z"},
                "OrgnlGrpInfAndSts": {"OrgnlMsgId": "RTP20250315CITI0000000555", "OrgnlMsgNmId": "pacs.008.001.07", "GrpSts": "ACCP"},
                "TxInfAndSts": {
                    "OrgnlTxId": "RTP20250315TXN000000555",
                    "OrgnlUETR": _UETR_RTP,
                    "TxSts": "ACCP",
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "TCH"}},
                    "AccptncDtTm": "2025-03-15T18:05:45.888Z",
                    "FctvIntrBkSttlmDt": "2025-03-15"
                }
            }
        }
    },
    "iso20022_actc_intermediate": {
        "_note": "Intermediate ACTC from TCH — technical validation passed, routing in progress",
        "TxInfAndSts": {"OrgnlUETR": _UETR_RTP, "TxSts": "ACTC", "AccptncDtTm": "2025-03-15T18:05:34.210Z"}
    },
    "flattened": {
        "network": "RTP",
        "message_type": "Payment Status Report",
        "original_uetr": _UETR_RTP,
        "final_status": "ACCP",
        "total_turnaround_ms": 12371,
        "status_timeline": [
            {"status": "ACTC", "offset_ms": 489, "note": "TCH validated"},
            {"status": "ACWP", "offset_ms": 8200, "note": "Receiver accepted"},
            {"status": "ACCP", "offset_ms": 12371, "note": "Funds posted"}
        ]
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  RTP — pacs.004.001.08  RETURN
# ═══════════════════════════════════════════════════════════════════════════

RTP_RETURN: Dict[str, Any] = {
    "_metadata": {
        "network": "RTP",
        "message_type": "pacs.004.001.08",
        "description": "Payment Return — RTP version, full returns only, within 2 business days",
        "common_return_codes": {"AC04": "Closed account", "AM09": "Wrong amount", "CUST": "Customer request", "DUPL": "Duplicate", "FRAD": "Fraud"}
    },
    "iso20022": {
        "AppHdr": {
            "Fr": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"MmbId": _WFB_ABA}}}},
            "To": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"MmbId": _CITI_ABA}}}},
            "MsgDefIdr": "pacs.004.001.08",
            "CreDtTm": "2025-03-16T10:22:14.331Z"
        },
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pacs.004.001.08",
            "PmtRtr": {
                "GrpHdr": {
                    "MsgId": "RTPRETURN20250316WFB000001",
                    "CreDtTm": "2025-03-16T10:22:14.331Z",
                    "NbOfTxs": "1",
                    "TtlRtrdIntrBkSttlmAmt": {"@Ccy": "USD", "#text": "3850.75"},
                    "IntrBkSttlmDt": "2025-03-16",
                    "SttlmInf": {"SttlmMtd": "CLRG", "ClrSys": {"Cd": "TCH"}}
                },
                "TxInf": {
                    "RtrId": "RTPRET20250316WFB0000001",
                    "OrgnlGrpInf": {"OrgnlMsgId": "RTP20250315CITI0000000555", "OrgnlMsgNmId": "pacs.008.001.07"},
                    "OrgnlTxId": "RTP20250315TXN000000555",
                    "OrgnlUETR": _UETR_RTP,
                    "RtrdIntrBkSttlmAmt": {"@Ccy": "USD", "#text": "3850.75"},
                    "IntrBkSttlmDt": "2025-03-16",
                    "RtrRsnInf": {"Rsn": {"Cd": "DUPL"}, "AddtlInf": "Duplicate payment detected for invoice PCC-INV-2025-0115."}
                }
            }
        }
    },
    "flattened": {
        "network": "RTP",
        "message_type": "Payment Return",
        "return_id": "RTPRET20250316WFB0000001",
        "return_amount": 3850.75,
        "return_reason_code": "DUPL",
        "original_uetr": _UETR_RTP
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  RTP — pain.013 / pain.014  REQUEST FOR PAYMENT
# ═══════════════════════════════════════════════════════════════════════════

RTP_RFP: Dict[str, Any] = {
    "_metadata": {"network": "RTP", "message_type": "pain.013.001.06", "description": "Request for Payment via RTP"},
    "iso20022": {
        "AppHdr": {
            "Fr": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"MmbId": _WFB_ABA}}}},
            "To": {"FIId": {"FinInstnId": {"ClrSysMmbId": {"MmbId": _CITI_ABA}}}},
            "MsgDefIdr": "pain.013.001.06",
            "CreDtTm": "2025-03-14T16:00:00.000Z"
        },
        "Document": {
            "@xmlns": "urn:iso:std:iso:20022:tech:xsd:pain.013.001.06",
            "CdtrPmtActvtnReq": {
                "GrpHdr": {"MsgId": "RTPRFP20250314WFB0000001", "CreDtTm": "2025-03-14T16:00:00.000Z", "NbOfTxs": "1", "CtrlSum": "3850.75"},
                "PmtInf": {
                    "PmtInfId": "RTPRFP20250314WFB0000001PMT",
                    "PmtMtd": "TRF",
                    "ReqdExctnDt": {"Dt": "2025-03-15"},
                    "XpryDt": {"Dt": "2025-03-16"},
                    "Dbtr": {"Nm": "GlobalTech Solutions Inc"},
                    "DbtrAcct": {"Id": {"Othr": {"Id": "7654321098765432", "SchmeNm": {"Cd": "BBAN"}}}},
                    "DbtrAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _CITI_ABA}}},
                    "CdtTrfTxInf": {
                        "PmtId": {"EndToEndId": "E2E-RFP-PCCONSULT-20250315", "UETR": _UETR_RFP_R},
                        "Amt": {"InstdAmt": {"@Ccy": "USD", "#text": "3850.75"}},
                        "CdtrAgt": {"FinInstnId": {"ClrSysMmbId": {"ClrSysId": {"Cd": "USABA"}, "MmbId": _WFB_ABA}}},
                        "Cdtr": {"Nm": "Pacific Coast Consulting LLC"},
                        "CdtrAcct": {"Id": {"Othr": {"Id": "1122334455667788", "SchmeNm": {"Cd": "BBAN"}}}},
                        "RmtInf": {"Ustrd": "Invoice PCC-INV-2025-0115 — Consulting services March 2025 — due 2025-03-15"}
                    }
                }
            }
        }
    },
    "flattened": {
        "network": "RTP", "message_type": "Request for Payment",
        "rfp_id": "RTPRFP20250314WFB0000001",
        "uetr": _UETR_RFP_R, "amount": 3850.75, "currency": "USD",
        "requested_execution_date": "2025-03-15", "expiry_date": "2025-03-16"
    }
}

RTP_RFP_RESPONSE: Dict[str, Any] = {
    "_metadata": {"network": "RTP", "message_type": "pain.014.001.06", "description": "RfP Response"},
    "iso20022_acceptance": {
        "TxInfAndSts": {"TxSts": "ACCP", "OrgnlUETR": _UETR_RFP_R, "AccptncDtTm": "2025-03-15T08:34:15.222Z"}
    },
    "iso20022_rejection": {
        "TxInfAndSts": {"TxSts": "RJCT", "OrgnlUETR": _UETR_RFP_R, "StsRsnInf": {"Rsn": {"Cd": "AM04"}, "AddtlInf": "Insufficient funds."}}
    },
    "flattened": {
        "network": "RTP", "message_type": "RfP Response",
        "acceptance": {"status": "ACCP"}, "rejection": {"status": "RJCT", "reason_code": "AM04"}
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  ZELLE — SEND PAYMENT
# ═══════════════════════════════════════════════════════════════════════════

ZELLE_SEND_PAYMENT: Dict[str, Any] = {
    "_metadata": {
        "network": "Zelle (Early Warning Services)",
        "message_type": "Payment Initiation",
        "api_endpoint": "POST /api/v1/payments/zelle",
        "critical_differences": {
            "recipient_id": "Email or phone token — no account numbers exchanged",
            "reversals": "COMPLETED payments are FINAL and IRREVOCABLE",
            "rfp": "NOT supported",
            "limits": "Bank-set (~$500–$2500/day), not network-wide"
        }
    },
    "api_request": {
        "_endpoint": "POST /api/v1/payments/zelle",
        "payments": {
            "requestedExecutionDate": "2025-03-15",
            "paymentIdentifiers": {"endToEndId": "E2E-ZELLE-20250315-0001"},
            "paymentCurrency": "USD",
            "paymentAmount": 425.00,
            "transferType": "CREDIT",
            "memo": "March rent split — apartment utilities",
            "debtor": {
                "debtorName": "Sarah J. Williams",
                "debtorAccount": {"accountId": "9988776655443322", "accountType": "CHECKING"}
            },
            "debtorAgent": {"financialInstitutionId": {"bic": "CHASUS33", "clearingSystemMemberId": {"clearingSystemId": "USABA", "memberId": _JPMC_ABA}}},
            "creditor": {
                "creditorName": "Marcus T. Rivera",
                "creditorAccount": {"accountType": "ZELLE", "alternateAccountIdentifier": "marcus.rivera@gmail.com", "schemeName": {"proprietary": "EMAL"}}
            }
        }
    },
    "api_response_completed": {
        "_http_status": 201,
        "payments": {
            "paymentId": "ZEL20250315JPMC000078901",
            "firmRootId": "FROOTJPMC20250315001",
            "endToEndId": "E2E-ZELLE-20250315-0001",
            "createDateTime": "2025-03-15T14:23:45.521Z",
            "paymentStatus": "COMPLETED",
            "paymentAmount": 425.00,
            "paymentCurrency": "USD",
            "actualSettlementDate": "2025-03-15",
            "zelleNetworkTransactionId": "ZNT20250315ABCDEF123456",
            "recipientEnrollmentStatus": "ENROLLED"
        }
    },
    "api_response_pending": {
        "_http_status": 201,
        "payments": {
            "paymentId": "ZEL20250315JPMC000078902",
            "paymentStatus": "PENDING",
            "paymentStatusDetail": "Recipient not enrolled. Invitation sent. Expires 2025-03-29.",
            "recipientEnrollmentStatus": "NOT_ENROLLED"
        }
    },
    "flattened": {
        "network": "Zelle",
        "message_type": "Payment Send",
        "amount": 425.00,
        "currency": "USD",
        "sender_account": "9988776655443322",
        "recipient_token": "marcus.rivera@gmail.com",
        "token_type": "EMAIL",
        "status": "COMPLETED",
        "is_reversible": False
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  ZELLE — PAYMENT STATUS
# ═══════════════════════════════════════════════════════════════════════════

ZELLE_PAYMENT_STATUS: Dict[str, Any] = {
    "_metadata": {
        "network": "Zelle",
        "message_type": "Payment Status",
        "api_endpoint": "GET /api/v1/payments/zelle/{paymentId}",
        "status_values": {
            "COMPLETED": "Final — funds credited, non-reversible",
            "PENDING": "Recipient not enrolled — can cancel before expiry",
            "REJECTED": "Failed — sender NOT charged",
            "CANCELLED": "Cancelled while PENDING"
        }
    },
    "api_response_completed": {
        "_http_status": 200,
        "payments": {
            "paymentId": "ZEL20250315JPMC000078901",
            "paymentStatus": "COMPLETED",
            "paymentAmount": 425.00,
            "paymentCurrency": "USD",
            "createDateTime": "2025-03-15T14:23:45.521Z",
            "lastUpdatedDateTime": "2025-03-15T14:24:12.107Z",
            "processingTime": {"submitToCompleteMs": 26586}
        }
    },
    "api_response_rejected": {
        "_http_status": 200,
        "payments": {
            "paymentId": "ZEL20250315JPMC000078905",
            "paymentStatus": "REJECTED",
            "exceptions": {
                "errorCode": "DAILY_LIMIT_EXCEEDED",
                "errorDescription": "Payment exceeds daily sending limit. Current limit: USD 1000.00.",
                "retryable": False
            }
        }
    },
    "rejection_codes": {
        "DAILY_LIMIT_EXCEEDED": "Bank-set daily limit breached",
        "INSUFFICIENT_FUNDS": "Sender account balance insufficient",
        "RECIPIENT_NOT_ENROLLED_EXPIRED": "14-day enrollment window expired",
        "INVALID_TOKEN": "Email/phone not associated with Zelle",
        "ACCOUNT_RESTRICTED": "Fraud hold or restriction on account",
        "DUPLICATE_PAYMENT": "Same EndToEndId already processed",
        "FRAUD_BLOCKED": "Blocked by EWS or bank fraud rules",
        "SERVICE_UNAVAILABLE": "Zelle network temporarily down — retry"
    },
    "flattened": {
        "network": "Zelle",
        "message_type": "Status",
        "completed": {"status": "COMPLETED", "processing_time_seconds": 26.6, "is_reversible": False},
        "rejected": {"status": "REJECTED", "error_code": "DAILY_LIMIT_EXCEEDED", "debited": False}
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  ZELLE — RETURN / CANCELLATION
# ═══════════════════════════════════════════════════════════════════════════

ZELLE_RETURN_CANCELLATION: Dict[str, Any] = {
    "_metadata": {
        "network": "Zelle",
        "message_type": "Cancellation / Return",
        "critical_warning": "COMPLETED Zelle payments are FINAL. No network-level reversal exists.",
        "options": {
            "PENDING_CANCEL": "DELETE /api/v1/payments/zelle/{paymentId} — only while PENDING",
            "VOLUNTARY_RETURN": "Recipient initiates a new Zelle payment back to sender",
            "BANK_DISPUTE": "Reg E unauthorized transfer claim — 10 business days provisional credit"
        }
    },
    "cancellation_request": {
        "_endpoint": "DELETE /api/v1/payments/zelle/{paymentId}",
        "_path_param": {"paymentId": "ZEL20250315JPMC000078902"},
        "_body": {"cancellationReason": "CUSTOMER_REQUEST", "cancellationNote": "Customer wishes to cancel before enrollment."}
    },
    "cancellation_response_success": {
        "_http_status": 200,
        "payments": {
            "paymentId": "ZEL20250315JPMC000078902",
            "paymentStatus": "CANCELLED",
            "cancelledAt": "2025-03-15T16:05:33.221Z",
            "refundNote": "Payment was PENDING — sender was not charged."
        }
    },
    "cancellation_response_too_late": {
        "_http_status": 409,
        "error": {
            "errorCode": "CANCELLATION_NOT_PERMITTED",
            "errorDescription": "Payment is COMPLETED and cannot be cancelled. File a dispute with your bank if fraud is suspected.",
            "regulatoryReference": "Regulation E (12 CFR 1005)"
        }
    },
    "bank_dispute_payload": {
        "disputeId": "DSP20250316JPMC000001",
        "claimType": "UNAUTHORIZED_TRANSFER",
        "regulatoryBasis": "REGULATION_E",
        "originalPayment": {"paymentId": "ZEL20250315JPMC000078901", "amount": 425.00, "completedAt": "2025-03-15T14:24:12.107Z"},
        "claim": {"description": "Customer did not authorise. Device stolen.", "requestedResolution": "FULL_REFUND"},
        "regulatoryDeadlines": {"provisionalCreditDeadline": "2025-03-26", "finalResolutionDeadline": "2025-05-15"}
    },
    "flattened": {
        "network": "Zelle", "message_type": "Cancellation / Return",
        "cancellation": {"applies_to": "PENDING only", "endpoint": "DELETE /api/v1/payments/zelle/{paymentId}"},
        "completed_return_options": ["Voluntary return (new payment from recipient)", "Bank dispute (Reg E) — 10 biz days provisional credit"]
    }
}


# ═══════════════════════════════════════════════════════════════════════════
#  FILE GENERATION — writes all samples to the directory structure
# ═══════════════════════════════════════════════════════════════════════════

ALL_SAMPLES = {
    "fednow/pacs008_credit_transfer.json":   FEDNOW_CREDIT_TRANSFER,
    "fednow/pacs002_payment_status.json":    FEDNOW_PAYMENT_STATUS,
    "fednow/pacs004_return.json":            FEDNOW_RETURN,
    "fednow/pain013_request_for_payment.json": FEDNOW_RFP,
    "fednow/pain014_rfp_response.json":      FEDNOW_RFP_RESPONSE,
    "fednow/lmt_liquidity_transfer.json":    FEDNOW_LIQUIDITY,
    "rtp/pacs008_credit_transfer.json":      RTP_CREDIT_TRANSFER,
    "rtp/pacs002_payment_status.json":       RTP_PAYMENT_STATUS,
    "rtp/pacs004_return.json":               RTP_RETURN,
    "rtp/pain013_request_for_payment.json":  RTP_RFP,
    "rtp/pain014_rfp_response.json":         RTP_RFP_RESPONSE,
    "zelle/send_payment.json":               ZELLE_SEND_PAYMENT,
    "zelle/payment_status.json":             ZELLE_PAYMENT_STATUS,
    "zelle/return_reversal.json":            ZELLE_RETURN_CANCELLATION,
}


def save_to_files(output_dir: str = ".") -> None:
    """Write all payment sample dicts to individual JSON files."""
    written = []
    for rel_path, sample in ALL_SAMPLES.items():
        full_path = os.path.join(output_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=2, ensure_ascii=False)
        written.append(full_path)
        print(f"  ✓  {full_path}")
    print(f"\n  Written {len(written)} files to: {os.path.abspath(output_dir)}")


def get_sample(network: str, message_type: str) -> Dict[str, Any]:
    """
    Retrieve a sample by network and message type.

    Examples:
        get_sample("fednow", "credit_transfer")
        get_sample("rtp", "payment_status")
        get_sample("zelle", "send_payment")
    """
    key = f"{network.lower()}_{message_type.lower()}"
    mapping = {
        "fednow_credit_transfer": FEDNOW_CREDIT_TRANSFER,
        "fednow_payment_status":  FEDNOW_PAYMENT_STATUS,
        "fednow_return":          FEDNOW_RETURN,
        "fednow_rfp":             FEDNOW_RFP,
        "fednow_rfp_response":    FEDNOW_RFP_RESPONSE,
        "fednow_liquidity":       FEDNOW_LIQUIDITY,
        "rtp_credit_transfer":    RTP_CREDIT_TRANSFER,
        "rtp_payment_status":     RTP_PAYMENT_STATUS,
        "rtp_return":             RTP_RETURN,
        "rtp_rfp":                RTP_RFP,
        "rtp_rfp_response":       RTP_RFP_RESPONSE,
        "zelle_send_payment":     ZELLE_SEND_PAYMENT,
        "zelle_payment_status":   ZELLE_PAYMENT_STATUS,
        "zelle_return":           ZELLE_RETURN_CANCELLATION,
        "zelle_return_cancellation": ZELLE_RETURN_CANCELLATION,
    }
    if key not in mapping:
        raise KeyError(f"No sample for '{key}'. Available: {sorted(mapping)}")
    return mapping[key]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate all payment sample JSON files")
    parser.add_argument("--output-dir", default=".", help="Root directory to write files into (default: current directory)")
    args = parser.parse_args()
    print(f"\nGenerating payment sample files → {os.path.abspath(args.output_dir)}\n")
    save_to_files(args.output_dir)
