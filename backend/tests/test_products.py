def test_create_and_read(client, signed_in):
    created = client.post("/products/", json={"name": "Niacinamide", "brand": "The Ordinary"})
    assert created.status_code == 201
    product_id = created.json()["id"]

    fetched = client.get(f"/products/{product_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Niacinamide"


def test_blank_name_rejected(client, signed_in):
    assert client.post("/products/", json={"name": ""}).status_code == 422


def test_missing_product_is_404(client, signed_in):
    assert client.get("/products/999").status_code == 404


def test_patch_leaves_omitted_fields_alone(client, product):
    response = client.patch(f"/products/{product['id']}", json={"notes": "pea size"})
    assert response.status_code == 200
    body = response.json()
    assert body["notes"] == "pea size"
    assert body["brand"] == "CeraVe"  # not nulled by omission


def test_delete_archives_and_hides(client, product):
    assert client.delete(f"/products/{product['id']}").status_code == 204

    assert client.get("/products/") .json() == []
    archived = client.get("/products/?include_archived=true").json()
    assert len(archived) == 1
    assert archived[0]["archived_at"] is not None

    # Archiving keeps the row, so it is still addressable and its history survives.
    assert client.get(f"/products/{product['id']}").status_code == 200
