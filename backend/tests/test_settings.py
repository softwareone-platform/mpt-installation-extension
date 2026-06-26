from mpt_installation_extension.settings import ExtensionSettings


def test_loads_product_extension_mapping():
    expected_mapping = {
        "PRD-1111": ["EXT-1111", "EXT-2222"],
    }

    result = ExtensionSettings.load()

    assert result.product_extension_mapping == expected_mapping
    assert result.product_ids == ("PRD-1111",)
    assert result.product_ids_rql == "(PRD-1111)"
