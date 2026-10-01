"""Typed domain exceptions, mapped to HTTP status codes in ``main.py``."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for business-rule violations."""

    status_code = 400


class NotFoundError(DomainError):
    """Requested entity does not exist."""

    status_code = 404


class UnbalancedEntryError(DomainError):
    """A journal entry's debits and credits do not match."""

    status_code = 422


class InsufficientStockError(DomainError):
    """A movement would drive an item's quantity below zero."""

    status_code = 422


class StockMovedError(DomainError):
    """An item has moved since a transaction, so undoing it would misprice what is left.

    Reversing takes a transaction back out at exactly the value it came in at. If
    the item has moved since — sold, consumed, or topped up — subtracting the old
    value leaves the remainder valued at a number that never existed. The later
    transactions have to be reversed first, which puts the item back where it was
    when this one was posted.
    """

    status_code = 409


class DuplicateError(DomainError):
    """A unique identifier (account code, voucher number) already exists."""

    status_code = 409


class PermissionDeniedError(DomainError):
    """The acting role is not permitted to perform this action."""

    status_code = 403


class ApprovalRequiredError(DomainError):
    """The action is paused: a second person must approve it first."""

    status_code = 409
