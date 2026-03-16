# STORY-0.4 – Define Data Contract and Pydantic Schema Models

| Field | Value |
|-------|-------|
| **Story ID** | STORY-0.4 |
| **Epic** | [EPIC-0 – PayCenter Infrastructure Discovery](../epics/EPIC-0-paycenter-infrastructure-discovery.md) |
| **Status** | 🔴 Blocked – Requires STORY-0.2 |
| **Points** | 5 |
| **Priority** | P0 – Critical Path |

## User Story

As a bridge service developer, I need formal Pydantic v2 data models for the raw PayCenter event payloads so that EPIC-1 development can proceed with accurate, type-safe deserialization and validation.

## Background

EPIC-1 (STORY-1.3) requires a `PayCenterEvent` Pydantic model for deserializing and validating incoming messages. That model cannot be written until the confirmed schemas from STORY-0.2 are available. This story turns those schemas into the official data contract that all subsequent EPIC-1 stories depend on.

## Acceptance Criteria

- [ ] Pydantic v2 models created in `src/models/paycenter.py` for all three rail types
- [ ] Base model `PayCenterEvent` captures common fields present across all rails
- [ ] Rail-specific submodels created: `ZelleEvent`, `RTPEvent`, `FedNowEvent` (or discriminated union, TBD based on schema structure)
- [ ] All PII fields annotated with a custom type or field alias to make tokenization targets explicit
- [ ] Models include field-level validation (e.g. enums for status, non-null transaction IDs)
- [ ] Model unit tests added in `tests/unit/test_models_paycenter.py` using example payloads from `docs/schemas/paycenter/`
- [ ] `docs/schemas/paycenter/README.md` updated to reference the Pydantic models as the authoritative data contract

## Model Structure (draft — to be finalized based on confirmed schemas)

```python
# src/models/paycenter.py

from pydantic import BaseModel
from enum import Enum
from typing import Optional

class RailType(str, Enum):
    ZELLE = "ZELLE"
    RTP = "RTP"
    FEDNOW = "FEDNOW"

class PaymentStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETURNED = "RETURNED"
    PENDING = "PENDING"

class PayCenterEvent(BaseModel):
    """Base model — common fields across all PayCenter rails. Field names TBD from confirmed schema."""
    rail_type: RailType
    transaction_id: str
    payment_status: PaymentStatus
    institution_id: str
    # ... additional confirmed fields
```

> ⚠️ Field names above are illustrative. Final names must match confirmed PayCenter payload from STORY-0.2.

## Definition of Done

- [ ] `src/models/paycenter.py` committed with all rail models
- [ ] All model unit tests pass (`pytest tests/unit/test_models_paycenter.py`)
- [ ] EPIC-1 STORY-1.3 can be implemented against these models without further schema discovery
- [ ] Old draft model references (if any) removed from codebase
