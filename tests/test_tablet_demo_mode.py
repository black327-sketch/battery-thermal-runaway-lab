from app.utils.ui_theme import is_tablet_demo_mode


class _QueryParams(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def test_tablet_demo_mode_from_query_param(monkeypatch):
    state = {}

    class FakeStreamlit:
        query_params = _QueryParams({"demo": "tablet"})
        session_state = state

    monkeypatch.setattr("app.utils.ui_theme.st", FakeStreamlit)

    assert is_tablet_demo_mode() is True
    assert state["tablet_demo_mode"] is True


def test_tablet_demo_mode_defaults_false(monkeypatch):
    class FakeStreamlit:
        query_params = _QueryParams({})
        session_state = {}

    monkeypatch.setattr("app.utils.ui_theme.st", FakeStreamlit)

    assert is_tablet_demo_mode() is False
