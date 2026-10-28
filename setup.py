"""setuptools entry with build hooks for knowledge resource staging."""
from pathlib import Path
import sys

# Ensure repo-root helpers are importable during build from checkout or sdist.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aipf_packaging.build_hooks import build_py, sdist  # noqa: E402
from setuptools import setup

setup(cmdclass={"build_py": build_py, "sdist": sdist})
