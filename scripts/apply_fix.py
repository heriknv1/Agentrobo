#!/usr/bin/env python3
"""Patch público e restrito para empacotamento Windows do Monaw v1.1.0.

Não acessa credenciais, conversas, configurações nem arquivos locais do usuário.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ORIGINAL_LOOP = 'for package in ("tiktoken", "tiktoken_ext", "scrapling", "mcp", "uvicorn"):'

ADDITION = '''\n# Windows UI Automation modules are used through lazy imports at runtime.\n# Collect their binaries and submodules explicitly for PyInstaller.\nfor package in ("pywinauto", "comtypes", "mss", "PIL", "win32", "win32com"):\n    package_datas, package_binaries, package_hidden = collect_all(package)\n    datas += package_datas\n    binaries += package_binaries\n    hiddenimports += package_hidden\n\nhiddenimports += [\n    "pywinauto", "comtypes", "pythoncom", "pywintypes",\n    "win32api", "win32con", "win32gui", "win32process",\n    "win32event", "win32clipboard", "win32file", "win32security",\n    "win32ui", "win32gui_struct", "win32timezone",\n]\n'''

OLD_UIA = '''def _uia_available() -> bool:\n    """Check if pywinauto is importable."""\n    try:\n        import pywinauto  # noqa: F401\n        return True\n    except ImportError:\n        return False\n'''

NEW_UIA = '''def _uia_available() -> bool:\n    """Check if pywinauto is importable; log the actual dependency failure."""\n    try:\n        import pywinauto  # noqa: F401\n        return True\n    except ImportError as exc:\n        import logging\n        logging.getLogger(__name__).warning(\n            "Windows UIA import failed (pywinauto or dependency): %s", exc, exc_info=True\n        )\n        return False\n'''


def replace_exact(path: Path, old: str, new: str) -> None:
    body = path.read_text(encoding="utf-8")
    count = body.count(old)
    if count != 1:
        raise RuntimeError(f"Unexpected upstream file format in {path}: expected 1 anchor, found {count}")
    path.write_text(body.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"Patched {path}")


def run(root: Path) -> None:
    spec = root / "backend" / "packaging" / "monaw-backend.spec"
    tools = root / "backend" / "app" / "skills" / "computer_use" / "window_ops.py"
    for path in (spec, tools):
        if not path.is_file():
            raise FileNotFoundError(path)
    spec_text = spec.read_text(encoding="utf-8")
    if ADDITION.strip() not in spec_text:
        anchor = "\na = Analysis(\n"
        if ORIGINAL_LOOP not in spec_text or spec_text.count(anchor) != 1:
            raise RuntimeError("Monaw spec differs from verified v1.1.0; refusing patch")
        replace_exact(spec, anchor, ADDITION + anchor)
    tools_text = tools.read_text(encoding="utf-8")
    if NEW_UIA not in tools_text:
        replace_exact(tools, OLD_UIA, NEW_UIA)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("monaw_root", type=Path)
    args = parser.parse_args()
    run(args.monaw_root.resolve())
