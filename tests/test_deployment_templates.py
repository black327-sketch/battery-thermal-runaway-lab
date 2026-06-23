from pathlib import Path


def test_deployment_templates_include_websocket_and_safe_secret_paths():
    nginx = Path("deploy/nginx-streamlit.conf.example").read_text(encoding="utf-8")
    service = Path("deploy/digital-lab.service.example").read_text(encoding="utf-8")
    guide = Path("DEPLOYMENT_GUIDE.md").read_text(encoding="utf-8")

    assert "proxy_set_header Upgrade $http_upgrade" in nginx
    assert "proxy_set_header Connection \"upgrade\"" in nginx
    assert "EnvironmentFile=-/etc/digital-lab/digital-lab.env" in service
    assert "Restart=on-failure" in service
    assert "sk-REPLACE_WITH_REAL_KEY" in guide
    assert ".streamlit/secrets.toml" in Path(".gitignore").read_text(encoding="utf-8")
    assert "backups/" in Path(".gitignore").read_text(encoding="utf-8")
    assert "artifacts/" in Path(".gitignore").read_text(encoding="utf-8")
