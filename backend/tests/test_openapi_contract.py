from app.main import app


def test_journal_openapi_keeps_generation_and_edit_contract_fields():
    schemas = app.openapi()["components"]["schemas"]

    generate_properties = schemas["JournalGenerateRequest"]["properties"]
    update_properties = schemas["JournalUpdateRequest"]["properties"]

    assert "templateId" in generate_properties
    assert "captions" in update_properties
    assert "sections" in update_properties
    assert "layoutVariant" in update_properties
