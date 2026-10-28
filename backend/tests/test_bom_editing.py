"""The recipe (BOM): adding, correcting and removing components over HTTP.

A recipe could previously only arrive from a workbook import, which meant the
first time the client launched a new product there was no way to say what it is
made of — and Production Entry had nothing to scale. These cover the rules the
screen relies on: an edge needs two known items, cannot point at itself, cannot
close a loop, and re-adding one corrects its quantity instead of duplicating it.

A loop matters more here than elsewhere: ``explode_bom`` walks the tree
recursively, so a cycle would not merely show wrong figures, it would not
terminate.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

ADMIN = "admin@rpci.demo"
STORE = "store@rpci.demo"

# The seeded workbook defines these items but gives none of them a recipe, apart
# from TRD-018, which these deliberately avoid.
FINISHED = "FG001"
RAW = "RM001"
RAW_TWO = "RM002"


def _headers(login, email: str = ADMIN) -> dict[str, str]:
    status, body = login(email)
    assert status == 200, body
    return {"Authorization": f"Bearer {body['access_token']}"}


def _add(client: TestClient, headers: dict, parent: str, component: str, qty: str):
    return client.post(
        f"/api/items/{parent}/bom",
        headers=headers,
        json={"component_code": component, "qty_per_unit": qty},
    )


def test_adding_a_component_returns_the_whole_recipe(client, login) -> None:
    """The screen re-renders from the response, so it returns the full recipe."""
    headers = _headers(login)
    response = _add(client, headers, FINISHED, RAW, "2.5")
    assert response.status_code == 201, response.text

    recipe = response.json()
    assert len(recipe) == 1
    assert recipe[0]["component_code"] == RAW
    assert Decimal(recipe[0]["qty_per_unit"]) == Decimal("2.5")
    assert recipe[0]["component_name"]
    assert recipe[0]["uom"]


def test_a_component_is_not_duplicated_when_re_added(client, login) -> None:
    """Re-adding the same component corrects the quantity in place.

    Two rows for one input would be ambiguous: production reads one quantity per
    component, and the recipe would then depend on row order.
    """
    headers = _headers(login)
    _add(client, headers, FINISHED, RAW, "2.5")
    response = _add(client, headers, FINISHED, RAW, "3")

    assert response.status_code == 201, response.text
    recipe = response.json()
    assert len(recipe) == 1
    assert Decimal(recipe[0]["qty_per_unit"]) == Decimal("3")


def test_a_recipe_can_hold_several_components(client, login) -> None:
    headers = _headers(login)
    _add(client, headers, FINISHED, RAW, "2")
    _add(client, headers, FINISHED, RAW_TWO, "0.5")

    recipe = client.get(f"/api/items/{FINISHED}/bom", headers=headers).json()
    assert {r["component_code"] for r in recipe} == {RAW, RAW_TWO}


def test_a_component_can_be_removed(client, login) -> None:
    headers = _headers(login)
    _add(client, headers, FINISHED, RAW, "2")
    _add(client, headers, FINISHED, RAW_TWO, "0.5")

    response = client.delete(f"/api/items/{FINISHED}/bom/{RAW}", headers=headers)
    assert response.status_code == 200, response.text
    assert [r["component_code"] for r in response.json()] == [RAW_TWO]


def test_an_unknown_item_is_refused(client, login) -> None:
    headers = _headers(login)
    response = _add(client, headers, FINISHED, "NOT-AN-ITEM", "1")
    assert response.status_code == 404


def test_an_item_cannot_be_its_own_component(client, login) -> None:
    """Self-reference is the smallest possible loop, refused with a plain message."""
    headers = _headers(login)
    response = _add(client, headers, FINISHED, FINISHED, "1")
    assert response.status_code == 400
    assert "itself" in response.json()["detail"].lower()


def test_a_loop_is_refused(client, login) -> None:
    """A -> B then B -> A would make the recipe contain itself.

    ``explode_bom`` recurses through the tree, so this is refused at entry rather
    than guarded on every read.
    """
    headers = _headers(login)
    _add(client, headers, FINISHED, RAW, "2")

    response = _add(client, headers, RAW, FINISHED, "1")
    assert response.status_code == 400
    assert "itself" in response.json()["detail"].lower()


def test_a_deeper_loop_is_refused(client, login) -> None:
    """The check walks the whole subtree, not just the direct children."""
    headers = _headers(login)
    _add(client, headers, FINISHED, RAW, "2")
    _add(client, headers, RAW, RAW_TWO, "3")

    response = _add(client, headers, RAW_TWO, FINISHED, "1")
    assert response.status_code == 400


def test_a_non_positive_quantity_is_refused(client, login) -> None:
    """Zero or negative would produce free or negative material cost."""
    headers = _headers(login)
    assert _add(client, headers, FINISHED, RAW, "0").status_code == 422
    assert _add(client, headers, FINISHED, RAW, "-1").status_code == 422


def test_removing_a_component_that_is_not_there_is_refused(client, login) -> None:
    headers = _headers(login)
    response = client.delete(f"/api/items/{FINISHED}/bom/{RAW}", headers=headers)
    assert response.status_code == 404


def test_a_recipe_may_be_edited_by_store_staff(client, login) -> None:
    """Store/Production staff set up recipes; the matrix grants them items_bom."""
    headers = _headers(login, STORE)
    response = _add(client, headers, FINISHED, RAW, "1.5")
    assert response.status_code == 201, response.text


def test_a_new_recipe_drives_production_without_a_workbook(client, login) -> None:
    """The path this was added for: define a recipe by hand, then produce from it.

    Nothing here comes from a workbook — the item, the recipe and the run are all
    entered through the API, which is what "test from scratch" has to mean.
    """
    headers = _headers(login)

    created = client.post(
        "/api/items",
        headers=headers,
        json={
            "code": "ZTEST-FG",
            "name": "Test Finished Resin",
            "category": "Finished Good",
            "segment": "Manufacturing",
            "uom": "kg",
        },
    )
    assert created.status_code == 201, created.text

    _add(client, headers, "ZTEST-FG", RAW, "2")

    exploded = client.get(
        "/api/items/ZTEST-FG/explode", params={"qty": "5"}, headers=headers
    )
    assert exploded.status_code == 200, exploded.text
    body = exploded.json()
    assert [line["item_code"] for line in body["lines"]] == [RAW]
    assert Decimal(body["lines"][0]["qty_required"]) == Decimal("10")
