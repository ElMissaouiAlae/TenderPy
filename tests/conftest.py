"""Shared pytest configuration."""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests that load real models (e.g. bge-m3).",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: loads real models; run with --run-slow")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-slow"):
        return
    skip_slow = pytest.mark.skip(reason="slow test; run with --run-slow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
