import ast
import importlib
from pathlib import Path


def _python_files_to_check() -> list[Path]:
    return [Path("app/main.py"), *sorted(Path("app/pages").glob("*.py"))]


def test_streamlit_pages_only_import_existing_utils_objects():
    failures = []
    for path in _python_files_to_check():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if not node.module or not node.module.startswith("app.utils."):
                continue
            module = importlib.import_module(node.module)
            for alias in node.names:
                if alias.name == "*":
                    continue
                if not hasattr(module, alias.name):
                    failures.append(f"{path} 从 {node.module} 导入了不存在的对象 {alias.name}")
    assert not failures, "\n".join(failures)


def test_app_main_imports_without_missing_utils_symbols():
    importlib.import_module("app.main")
