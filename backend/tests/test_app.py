from mpt_installation_extension.app import ext_app


def test_app_has_no_registered_routes():
    routes = list(ext_app.routes)  # act

    assert routes == []
