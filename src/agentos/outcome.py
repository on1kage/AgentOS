from __future__ import annotations

from enum import Enum


class ExecutionOutcome(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


RUN_SUMMARY_SCHEMA_VERSION = 1
