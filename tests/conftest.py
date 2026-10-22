"""Shared pytest configuration for the test suite.

Only marker registration lives here. It adds no fixtures, no collection
behaviour, and no changes to how any existing test is selected or executed.
"""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register the opt-in marker used by private-evidence regression checks.

    ``private_evidence`` marks tests that read a real private EXP-019 run from a
    configured workstation. Such tests are skipped unless the operator sets
    ``AIPF_EXP019_PRIVATE_PRESERVATION`` to a truthy value, and they are never
    reported as passing verification when the private evidence is unavailable.
    """
    config.addinivalue_line(
        "markers",
        "private_evidence: opt-in check that reads a real private EXP-019 run; "
        "skipped unless AIPF_EXP019_PRIVATE_PRESERVATION is set to a truthy value",
    )
