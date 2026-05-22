"""Live endpoint checks for VecTrade Status.

Validates that all monitored endpoints are actually reachable:
- All configured sites respond
- Response times are reasonable
- HTTPS is properly configured
"""

from __future__ import annotations

from pathlib import Path

import pytest
import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def config() -> dict:
    """Load .upptimerc.yml."""
    return yaml.safe_load((ROOT / ".upptimerc.yml").read_text())


@pytest.fixture(scope="session")
def sites(config) -> list[dict]:
    """Get monitored sites list."""
    return config["sites"]


class TestEndpointsReachable:
    """Verify all monitored endpoints are live."""

    def test_all_sites_respond(self, sites):
        """Every configured site should respond with 2xx or 3xx."""
        failures = []
        for site in sites:
            try:
                resp = requests.get(
                    site["url"],
                    timeout=15,
                    headers={"User-Agent": "vectrade-status-checks/1.0"},
                    allow_redirects=True,
                )
                if resp.status_code >= 400:
                    failures.append(f"{site['name']} ({site['url']}): {resp.status_code}")
            except requests.RequestException as e:
                failures.append(f"{site['name']} ({site['url']}): {e}")
        assert not failures, f"Unreachable sites: {failures}"

    def test_main_site_responds(self, sites):
        """Main VecTrade site must be reachable."""
        main = next((s for s in sites if s["name"] == "VecTrade"), None)
        assert main is not None
        resp = requests.get(
            main["url"],
            timeout=15,
            headers={"User-Agent": "vectrade-status-checks/1.0"},
            allow_redirects=True,
        )
        assert resp.status_code < 400

    def test_api_health_responds(self, sites):
        """Trading API health endpoint must respond."""
        api = next((s for s in sites if "api" in s["url"]), None)
        if api is None:
            pytest.skip("No API endpoint configured")
        resp = requests.get(
            api["url"],
            timeout=15,
            headers={"User-Agent": "vectrade-status-checks/1.0"},
        )
        assert resp.status_code < 400


class TestPerformance:
    """Verify endpoint response times."""

    def test_response_times_reasonable(self, sites):
        """All sites should respond within 10 seconds."""
        import time

        slow = []
        for site in sites:
            try:
                start = time.time()
                requests.get(
                    site["url"],
                    timeout=10,
                    headers={"User-Agent": "vectrade-status-checks/1.0"},
                    allow_redirects=True,
                )
                elapsed = time.time() - start
                if elapsed > 10:
                    slow.append(f"{site['name']}: {elapsed:.1f}s")
            except requests.Timeout:
                slow.append(f"{site['name']}: TIMEOUT")
            except requests.RequestException:
                pass  # Reachability tested elsewhere
        assert not slow, f"Slow sites: {slow}"


class TestSSL:
    """Verify SSL/TLS configuration."""

    def test_all_sites_use_https(self, sites):
        """All sites must use HTTPS."""
        for site in sites:
            assert site["url"].startswith("https://"), f"Non-HTTPS: {site['name']}"
