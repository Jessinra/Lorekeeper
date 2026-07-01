from lorekeeper.infra.settings import Settings


def test_namespace_defaults_to_shared():
    s = Settings()
    assert s.namespace == "shared"


def test_namespace_reads_from_env(monkeypatch):
    monkeypatch.setenv("LORE_NAMESPACE", "diana")
    s = Settings()
    assert s.namespace == "diana"
