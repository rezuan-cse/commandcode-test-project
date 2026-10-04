"""The client owns their configuration, permanently.

The requirement is that they can change VAT rates, security settings, company
details and everything else themselves — at any time, without a programmer and
without a redeploy. Three things have to hold for that to be true, and all three
are tested here:

* **every** setting in the catalogue accepts a change through the API, not just the
  ones that happen to be convenient;
* a change takes effect **immediately**, in the running process — the business logic
  reads the stored value on every posting rather than a copy taken at boot;
* a change is **never quietly reset** — not by a later boot, and not by a redeploy.

That last one is the one that would embarrass everybody. A value silently reverting
to its default overnight is worse than one that was never editable, because the
client would believe the books were using the rate they had set.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest
from app.modules.settings import service as settings_service

ADMIN = "admin@rpci.demo"
ACCOUNTANT = "accountant@rpci.demo"


def _headers(login, email: str = ADMIN) -> dict[str, str]:
    status, body = login(email)
    assert status == 200, body
    return {"Authorization": f"Bearer {body['access_token']}"}


def _settings(client: TestClient, headers: dict[str, str]) -> list[dict]:
    response = client.get("/api/settings", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _set(client: TestClient, headers: dict[str, str], key: str, value: object):
    return client.patch(f"/api/settings/{key}", json={"value": value}, headers=headers)


def _value_for(setting: dict) -> object:
    """A value this setting should accept, chosen from what it says it is.

    For a `json` setting the value already stored is sent straight back: the shape
    of those differs per key (a list of components, a list of rate slabs), and
    guessing at a fresh one would test the guess rather than the update path.
    """
    kind = setting.get("value_type", "string")
    if kind == "bool":
        return "true"
    if kind == "number":
        return "7"
    if kind == "enum":
        options = setting.get("options") or []
        assert options, f"{setting['key']} is an enum with no options"
        return options[0]
    if kind == "json":
        return setting.get("value")
    return "TEST-VALUE"


def test_every_setting_can_be_changed(client, db, login) -> None:
    """The whole catalogue is editable, not a selected subset.

    Swept rather than sampled: the failure this guards against is one key that was
    seeded with a type the interface cannot round-trip, which nobody notices until
    the client tries to change exactly that one.
    """
    headers = _headers(login)
    settings = _settings(client, headers)
    assert len(settings) > 30, "expected the full catalogue"

    for setting in settings:
        response = _set(client, headers, setting["key"], _value_for(setting))
        assert response.status_code == 200, (
            f"{setting['key']} ({setting.get('value_type')}) could not be updated: "
            f"{response.text}"
        )


def test_a_silly_value_is_refused(client, db, login) -> None:
    """A typo must not be able to corrupt the books.

    The rate is used in every later calculation, so "1O%" has to be rejected at the
    door rather than stored and multiplied by.
    """
    headers = _headers(login)

    bad_number = _set(client, headers, "vat.standard_rate_pct", "not-a-number")
    assert bad_number.status_code == 400, bad_number.text

    bad_choice = _set(client, headers, "posting.approval_scope", "nonsense")
    assert bad_choice.status_code == 400, bad_choice.text


def test_a_change_takes_effect_without_a_restart(client, db, login) -> None:
    """Turn VAT on and the very next sale carries it — no redeploy involved."""
    headers = _headers(login)

    # Stock bought while VAT is off, so the cost is clean.
    purchases.post(
        db,
        PurchaseRequest(
            supplier="Stock Supplier",
            purchase_date=date(2026, 10, 12),
            lines=[
                PurchaseLineIn(
                    item_code="TRD001", qty=Decimal("10"), unit_cost=Decimal("1000")
                )
            ],
        ),
    )

    def sell() -> dict:
        response = client.post(
            "/api/sales",
            json={
                "customer": "Local Customer",
                "sale_date": "2026-10-12",
                "lines": [{"item_code": "TRD001", "qty": "2", "sale_price": "1500"}],
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        return response.json()["order"]

    assert Decimal(sell()["vat_total"]) == 0, "VAT should be off to start with"

    assert _set(client, headers, "vat.standard_rate_pct", "15").status_code == 200
    assert _set(client, headers, "vat.charge_vat", "true").status_code == 200

    # The same process, the same request handler, no restart — and now there is tax.
    assert Decimal(sell()["vat_total"]) > 0

    # And it can be turned off again just as easily, which is the point: nothing
    # about this is one-way.
    assert _set(client, headers, "vat.charge_vat", "false").status_code == 200
    assert Decimal(sell()["vat_total"]) == 0


def test_client_values_survive_a_restart(client, db, login) -> None:
    """A redeploy must not undo the client's configuration.

    `seed_defaults` runs on every boot to fill in gaps. This proves it fills *gaps*
    and nothing else: an existing value is left exactly as the client set it.
    Without this, a setting could silently revert overnight to the default the
    catalogue was written with — and every later calculation would quietly use the
    wrong rate.
    """
    headers = _headers(login)

    # A distinctive value in three different groups, so the test covers plans as
    # well as rates.
    chosen = {
        "company.phone": "01700-999888",
        "vat.standard_rate_pct": "7.5",
        "posting.books_closed_through": "2026-06-30",
    }
    for key, value in chosen.items():
        assert _set(client, headers, key, value).status_code == 200

    # What the application does on every start.
    settings_service.seed_defaults(db)
    db.commit()

    after = {row["key"]: row["value"] for row in _settings(client, headers)}
    for key, value in chosen.items():
        assert key in after, f"{key} disappeared"
        # The stored form is JSON, so a number comes back as "7.5" with quotes.
        assert str(value) in after[key], (
            f"{key} was reset to {after[key]} instead of keeping {value}"
        )


def test_settings_are_read_only_for_everyone_but_an_administrator(client, db, login) -> None:
    """The rates decide what the books say, so changing them is an administrator's job.

    A storekeeper can read the configuration — it explains the figures on their
    screen — but cannot alter a VAT rate.
    """
    accountant = _headers(login, ACCOUNTANT)
    assert client.get("/api/settings", headers=accountant).status_code == 200

    refused = _set(client, accountant, "vat.standard_rate_pct", "99")
    assert refused.status_code == 403, refused.text
