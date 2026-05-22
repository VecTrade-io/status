"""Validation tests for VecTrade Status configuration.

Tests verify:
- .upptimerc.yml has valid structure
- All monitored sites have required fields
- Configuration follows best practices
- GitHub repo config is correct
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def config() -> dict:
    """Load .upptimerc.yml."""
    return yaml.safe_load((ROOT / ".upptimerc.yml").read_text())


class TestUptimeConfig:
    """Validate .upptimerc.yml structure."""

    def test_has_owner(self, config):
        assert "owner" in config
        assert config["owner"] == "VecTrade-io"

    def test_has_repo(self, config):
        assert "repo" in config
        assert config["repo"] == "status"

    def test_has_sites(self, config):
        assert "sites" in config
        assert len(config["sites"]) > 0

    def test_has_status_website(self, config):
        assert "status-website" in config


class TestMonitoredSites:
    """Validate monitored site entries."""

    def test_all_sites_have_name(self, config):
        for site in config["sites"]:
            assert "name" in site, f"Site missing name: {site}"

    def test_all_sites_have_url(self, config):
        for site in config["sites"]:
            assert "url" in site, f"Site missing URL: {site}"

    def test_all_urls_are_https(self, config):
        for site in config["sites"]:
            assert site["url"].startswith("https://"), f"Non-HTTPS URL: {site['url']}"

    def test_urls_are_vectrade_domains(self, config):
        """All monitored URLs should be VecTrade-owned domains."""
        allowed_domains = ["vectrade.io"]
        for site in config["sites"]:
            url = site["url"]
            is_allowed = any(domain in url for domain in allowed_domains)
            assert is_allowed, f"URL not VecTrade domain: {url}"

    def test_minimum_sites_monitored(self, config):
        """Should monitor at least core services."""
        assert len(config["sites"]) >= 3

    @pytest.mark.parametrize("expected_name", [
        "VecTrade",
        "Documentation",
        "Trading API",
    ])
    def test_core_services_monitored(self, config, expected_name):
        """Core VecTrade services must be monitored."""
        names = [s["name"] for s in config["sites"]]
        assert expected_name in names, f"Missing core service: {expected_name}"


class TestStatusWebsite:
    """Validate status website configuration."""

    def test_has_cname(self, config):
        assert "cname" in config["status-website"]
        assert config["status-website"]["cname"] == "status.vectrade.io"

    def test_has_name(self, config):
        assert "name" in config["status-website"]

    def test_has_theme(self, config):
        assert "theme" in config["status-website"]

    def test_has_navbar(self, config):
        assert "navbar" in config["status-website"]
        assert len(config["status-website"]["navbar"]) > 0


class TestWorkflowSchedule:
    """Validate workflow schedule configuration."""

    def test_has_schedule(self, config):
        assert "workflowSchedule" in config

    def test_uptime_check_frequency(self, config):
        schedule = config["workflowSchedule"]
        assert "uptime" in schedule
        # Should check at least every 5 minutes
        assert "*/5" in schedule["uptime"] or "* *" in schedule["uptime"]


class TestOSSFiles:
    """Verify standard open-source files."""

    @pytest.mark.parametrize("filename", [
        "LICENSE",
        "README.md",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
    ])
    def test_file_exists(self, filename):
        assert (ROOT / filename).exists()

    def test_codeowners_exists(self):
        assert (ROOT / ".github" / "CODEOWNERS").exists()

    def test_dependabot_exists(self):
        assert (ROOT / ".github" / "dependabot.yml").exists()
