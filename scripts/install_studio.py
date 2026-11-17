#!/usr/bin/env python3
"""Bundle the Agentrobo Studio as a native Monaw skill, before PyInstaller.

The existing spec automatically bundles backend/app/skills/**/*. No credentials,
project data or user downloads are packaged into the PUBLIC GitHub artifact.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def install(root: Path):
    source = Path(__file__).resolve().parents[1] / "studio" / "skill"
    target = root.resolve() / "backend" / "app" / "skills" / "agentrobo_studio"
    if target.exists():
        raise RuntimeError("Refusing to overwrite an existing Studio skill")
    if not (root / "backend" / "packaging" / "monaw-backend.spec").exists():
        raise RuntimeError("Unsupported Monaw source revision")
    target.mkdir(parents=True, exist_ok=False)
    for filename in ("SKILL.md", "engine.py", "tools.py"):
        if not (source / filename).is_file():
            raise FileNotFoundError(source / filename)
        shutil.copy2(source / filename, target / filename)
    print(f"Bundled Monaw studio skill at: {target}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("monaw_root", type=Path)
    install(p.parse_args().monaw_root)
