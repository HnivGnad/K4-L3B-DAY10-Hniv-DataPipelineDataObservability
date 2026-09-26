"""Launcher for the Streamlit demo UI.

Usage:
    python script/run_ui.py
or directly:
    streamlit run app/main.py --server.port 8501
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _bootstrap_paths() -> Path:
    """Add project + src to PYTHONPATH so ``from core.config import ...`` works."""
    project_dir = Path(__file__).resolve().parents[1]
    src_path = project_dir / "src"
    sys.path.insert(0, str(project_dir))
    sys.path.insert(0, str(src_path))
    return project_dir


def _disable_noisy_watchers() -> None:
    """Tell Streamlit + Tornado not to introspect unrelated site-packages.

    When ``transformers`` (transitively imported by ``sentence_transformers``)
    is scanned for hot-reload, it tries to import ``torchvision`` which is
    not installed. Setting ``STREAMLIT_SERVER_FILE_WATCHER_TYPE=none`` skips
    the watcher entirely. We also pin STATIC_ASSETS and DISABLE USAGE STATS.
    """
    os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")
    os.environ.setdefault("STREAMLIT_GLOBAL_SUPPRESS_DEPRECATION_WARNINGS", "true")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_CLIENT_TOOLBAR_MODE", "minimal")


def main() -> None:
    _disable_noisy_watchers()
    project_dir = _bootstrap_paths()
    app_path = project_dir / "app" / "main.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(project_dir), str(project_dir / "src"), env.get("PYTHONPATH", ""))
        if part
    )
    command = [
        sys.executable, "-m", "streamlit", "run", str(app_path),
        "--server.port", "8501", "--server.headless", "false",
        "--browser.gatherUsageStats", "false", "--server.fileWatcherType", "none",
    ]
    print(f"Launching Streamlit with {sys.executable}")
    subprocess.run(command, cwd=project_dir, env=env, check=True)


if __name__ == "__main__":
    main()
