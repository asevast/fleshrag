"""Pytest configuration for smoke and integration tests."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "smoke: mark test as smoke test")
    config.addinivalue_line("markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(config, items):
    """Add markers based on test file location or name."""
    for item in items:
        if "smoke" in item.nodeid:
            item.add_marker(pytest.mark.smoke)
        elif "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
