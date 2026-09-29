"""Pydantic schemas for VAT summaries."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class VatSummary(BaseModel):
    """Output VAT, input VAT and the net payable over a period."""

    date_from: date
    date_to: date
    output_vat: Decimal
    input_vat: Decimal
    net_payable: Decimal
