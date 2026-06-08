"""E2E dashboard tests — real browser against a live uvicorn server.

All tests are gated behind ``@pytest.mark.e2e`` so they're excluded from the
default ``uv run pytest`` unit run.  Run with:

    uv run pytest tests/e2e/ -m e2e
"""

from __future__ import annotations

from typing import ClassVar

import requests
from playwright.sync_api import expect

# ===================================================================
# LKPR-59 AC 1: Memories tab renders seeded rows
# ===================================================================


class TestMemoriesLoad:
    """Seeded memories appear as rows on load."""

    def test_table_renders_rows(self, page, live_server: str) -> None:
        page.goto("/")
        rows = page.locator("[data-testid=memory-row]")
        # We seeded 5 memories
        expect(rows).to_have_count(5)
        # Check that each seeded title exists somewhere in the table
        for title in ["Test Memory One", "Alpha Project", "Beta Deployment"]:
            expect(page.locator(f"[data-testid=memory-row]:has-text('{title}')")).to_be_visible()

    def test_metadata_shows_memory_count(self, page, live_server: str) -> None:
        page.goto("/")
        # The metrics strip shows total memory count
        page.wait_for_selector("[data-testid=memory-row]")
        count_text = page.locator("#met-total").text_content()
        assert count_text == "5" or count_text == "5\n/", (
            f"Expected 5 memories, got {count_text}"
        )


# ===================================================================
# LKPR-59 AC 2: Search input filters rows
# ===================================================================


class TestSearch:
    """Typing in the search box narrows displayed rows."""

    def test_search_filters_by_title(self, page, live_server: str) -> None:
        page.goto("/")
        page.wait_for_selector("[data-testid=memory-row]")

        search = page.locator("[data-testid=mem-filter]")
        search.fill("Alpha")

        rows = page.locator("[data-testid=memory-row]")
        expect(rows).to_have_count(1)
        expect(rows.first).to_contain_text("Alpha Project")

    def test_search_filters_by_content(self, page, live_server: str) -> None:
        page.goto("/")
        page.wait_for_selector("[data-testid=memory-row]")

        search = page.locator("[data-testid=mem-filter]")
        search.fill("Docker")

        rows = page.locator("[data-testid=memory-row]")
        expect(rows).to_have_count(1)
        expect(rows.first).to_contain_text("Test Memory Two")

    def test_search_clear_shows_all(self, page, live_server: str) -> None:
        page.goto("/")
        page.wait_for_selector("[data-testid=memory-row]")

        search = page.locator("[data-testid=mem-filter]")
        search.fill("NONEXISTENT")
        rows = page.locator("[data-testid=memory-row]")
        expect(rows).to_have_count(0)

        search.fill("")
        page.wait_for_timeout(250)  # debounce 150 ms + buffer
        expect(rows).to_have_count(5)


# ===================================================================
# LKPR-59 AC 3: Delete removes from DOM and DB
# ===================================================================


class TestDelete:
    """Clicking delete removes the memory from both DOM and backend."""

    def test_hard_delete_removes_memory(self, page, live_server: str) -> None:
        page.goto("/")
        page.wait_for_selector("[data-testid=memory-row]")

        # Click the first memory row → opens detail tab
        rows = page.locator("[data-testid=memory-row]")
        first_title = rows.first.text_content()
        rows.first.click()

        # Should be on the detail tab now — click Edit
        page.wait_for_selector("[data-testid=detail-edit]")
        page.locator("[data-testid=detail-edit]").click()

        # Click Hard Delete
        page.wait_for_selector("[data-testid=detail-hard-delete]")

        # Accept the browser confirm() dialog
        page.once("dialog", lambda d: d.accept())
        page.locator("[data-testid=detail-hard-delete]").click()

        # Wait for the toast confirm
        page.wait_for_selector("[data-testid=toast]")

        # Should be back on the memories tab with 4 rows
        page.wait_for_selector("[data-testid=memory-row]")
        expect(page.locator("[data-testid=memory-row]")).to_have_count(4)

        # Verify via API that the deleted memory is gone
        resp = requests.get(f"{live_server}/api/memories", timeout=5)
        data = resp.json()
        titles = [m["title"] for m in data]
        assert first_title not in titles, f"{first_title} should have been deleted"


# ===================================================================
# LKPR-59 AC 4: Tab switching
# ===================================================================


class TestTabSwitching:
    """Each tab button shows the correct pane and hides others."""

    TAB_IDS: ClassVar[list[str]] = [
        "memories",
        "detail",
        "links",
        "query",
        "sessions",
        "config",
        "backup",
        "metrics",
    ]

    def test_each_tab_becomes_active(self, page, live_server: str) -> None:
        page.goto("/")

        for tab_name in self.TAB_IDS:
            tab_btn = page.locator(f"[data-testid=tab-{tab_name}]")
            tab_btn.click()
            page.wait_for_timeout(100)
            pane = page.locator(f"#tab-{tab_name}")
            class_attr = pane.get_attribute("class")
            assert class_attr and "active" in class_attr, (
                f"Tab {tab_name} pane missing 'active' class: {class_attr!r}"
            )

    def test_other_tabs_hidden_when_one_active(self, page, live_server: str) -> None:
        page.goto("/")

        # Start from Config tab
        page.locator("[data-testid=tab-config]").click()
        page.wait_for_timeout(100)

        # Only config should be active
        config_pane = page.locator("#tab-config")
        config_class = config_pane.get_attribute("class")
        assert config_class and "active" in config_class, (
            f"Config pane missing 'active' class: {config_class!r}"
        )

        memories_pane = page.locator("#tab-memories")
        memories_class = memories_pane.get_attribute("class")
        assert memories_class and "active" not in memories_class, (
            "Memories pane should not have 'active' class"
        )


# ===================================================================
# LKPR-59 AC 5: Config toggle saves to API, toast appears
# ===================================================================


class TestConfigToggle:
    """Changing a config value saves to the backend and shows a toast."""

    def test_change_config_and_save(self, page, live_server: str) -> None:
        page.goto("/")

        # Switch to Config tab
        page.locator("[data-testid=tab-config]").click()
        page.wait_for_selector("#cfg-weights", state="visible")

        # Grab a config input, change its value
        search_limit_input = page.locator("#cfg-search_limit")
        search_limit_input.fill("8")

        # Click Save
        page.locator("[data-testid=config-save]").click()

        # Toast should appear
        toast = page.locator("[data-testid=toast]")
        expect(toast).to_be_visible()

        # Verify via API
        resp = requests.get(f"{live_server}/api/config", timeout=5)
        config = resp.json()
        assert config["search_limit"] == 8, (
            f"Expected search_limit=8, got {config['search_limit']}"
        )

    def test_config_reload_after_save(self, page, live_server: str) -> None:
        """Config Reload button re-fetches from API without error."""
        page.goto("/")
        page.locator("[data-testid=tab-config]").click()
        page.wait_for_selector("#cfg-weights", state="visible")

        # Change and save
        page.locator("#cfg-search_limit").fill("3")
        page.locator("[data-testid=config-save]").click()
        page.wait_for_selector("[data-testid=toast]")

        # Click Reload (data-action="config:load") — reloads from API
        # The button labelled "Reset" actually reloads saved values from the backend
        page.locator("#tab-config button").filter(has_text="Reset").click()
        page.wait_for_timeout(300)

        # After reload, value should still be what we saved (3),
        # confirming the round-trip works correctly
        search_limit = page.locator("#cfg-search_limit").input_value()
        assert search_limit == "3", (
            f"Expected reload to preserve saved value 3, got {search_limit}"
        )
