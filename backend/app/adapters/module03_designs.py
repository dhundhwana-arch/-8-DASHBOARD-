"""Read-only validator and presenter for Module 03 (`-3-2D-CLOTHING-DESIGNER`) snapshots."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

DESIGN_ID_RE = re.compile(r"^DSG-[A-Z0-9-]{3,32}$")


class DesignReferenceSummary(BaseModel):
    """Read-only garment design reference parsed from a verified Module 03 snapshot."""

    model_config = ConfigDict(extra="forbid")

    design_id: str
    schema_version: str
    product_type: str
    fabric_id: str
    collar_style: str | None = None
    sleeve_style: str | None = None
    cuff_style: str | None = None
    fit_type: str | None = None


class _M03FabricRef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    fabric_id: str


class _M03SnapshotSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    design_id: str
    schema_version: str
    product_type: str
    fabric: _M03FabricRef
    components: dict[str, Any] = {}

    @field_validator("design_id")
    @classmethod
    def _check_design_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not DESIGN_ID_RE.match(cleaned):
            raise ValueError("design_id must start with 'DSG-'.")
        return cleaned

    @field_validator("schema_version")
    @classmethod
    def _check_version(cls, value: str) -> str:
        if not value.strip().startswith("1."):
            raise ValueError("Unsupported Module 03 schema_version.")
        return value.strip()


def summarize_design_snapshot(raw_snapshot: dict[str, Any] | None) -> DesignReferenceSummary | None:
    """Return a read-only summary when a valid Module 03 snapshot exists; otherwise ``None``."""
    if not raw_snapshot or not isinstance(raw_snapshot, dict):
        return None
    try:
        parsed = _M03SnapshotSchema.model_validate(raw_snapshot)
    except ValidationError:
        return None

    comps = parsed.components
    collar = comps.get("collar") if isinstance(comps.get("collar"), dict) else {}
    sleeves = comps.get("sleeves") if isinstance(comps.get("sleeves"), dict) else {}
    cuffs = comps.get("cuffs") if isinstance(comps.get("cuffs"), dict) else {}
    fit = comps.get("fit") if isinstance(comps.get("fit"), dict) else {}

    return DesignReferenceSummary(
        design_id=parsed.design_id,
        schema_version=parsed.schema_version,
        product_type=parsed.product_type,
        fabric_id=parsed.fabric.fabric_id,
        collar_style=collar.get("style"),
        sleeve_style=sleeves.get("style"),
        cuff_style=cuffs.get("style"),
        fit_type=fit.get("type"),
    )
