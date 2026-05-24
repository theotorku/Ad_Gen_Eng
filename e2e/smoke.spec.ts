import { test, expect, type Page } from "@playwright/test";

// Shell-only smoke tests. These exercise behaviors that do not depend on
// pre-existing campaign data, so the suite is safe to run against any
// deployment (live or local) without seeding fixtures.

async function clearAppState(page: Page) {
  await page.addInitScript(() => {
    try {
      window.localStorage.clear();
    } catch {
      // ignore
    }
  });
}

test.describe("ad gen engine shell", () => {
  test.beforeEach(async ({ page }) => {
    await clearAppState(page);
  });

  test("renders the workspace shell on cold load", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Ad Generation Engine/);
    await expect(page.getByRole("heading", { name: "New brief" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Today.+desk/ })).toBeVisible();
  });

  test("form starts empty and no channels are pressed", async ({ page }) => {
    await page.goto("/");
    const briefForm = page.getByRole("complementary");
    for (const name of ["Brand", "Product", "Objective", "Audience"]) {
      await expect(
        briefForm.getByRole("textbox", { name, exact: true }),
      ).toHaveValue("");
    }
    const channelGroup = page.getByRole("group", { name: /channels/i });
    const pressedStates = await channelGroup
      .getByRole("button")
      .evaluateAll((nodes) => nodes.map((n) => n.getAttribute("aria-pressed")));
    expect(pressedStates.every((s) => s === "false")).toBe(true);
  });

  test("Load sample brief populates the form and Clear empties it", async ({ page }) => {
    await page.goto("/");
    const briefForm = page.getByRole("complementary");
    const field = (name: string) =>
      briefForm.getByRole("textbox", { name, exact: true });

    await page.getByRole("button", { name: /load sample brief/i }).click();

    for (const name of ["Brand", "Product", "Objective", "Audience"]) {
      await expect(field(name)).not.toHaveValue("");
    }

    const channelGroup = page.getByRole("group", { name: /channels/i });
    const pressedAfterLoad = await channelGroup
      .getByRole("button")
      .evaluateAll((nodes) => nodes.map((n) => n.getAttribute("aria-pressed")));
    expect(pressedAfterLoad.some((s) => s === "true")).toBe(true);

    await page.getByRole("button", { name: /^clear$/i }).click();

    for (const name of ["Brand", "Product", "Objective", "Audience"]) {
      await expect(field(name)).toHaveValue("");
    }
    const pressedAfterClear = await channelGroup
      .getByRole("button")
      .evaluateAll((nodes) => nodes.map((n) => n.getAttribute("aria-pressed")));
    expect(pressedAfterClear.every((s) => s === "false")).toBe(true);
  });

  test("theme toggle flips data-theme and writes localStorage", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "New brief" })).toBeVisible();

    // Capture whatever the initial theme is (depends on stored value or the
    // host's prefers-color-scheme) and click the toggle exactly once.
    const initial = await page.evaluate(
      () => document.documentElement.dataset.theme,
    );
    expect(initial === "light" || initial === "dark").toBe(true);
    const flipped = initial === "dark" ? "light" : "dark";
    const toggleRe =
      initial === "dark" ? /switch to light mode/i : /switch to dark mode/i;
    await page.getByRole("button", { name: toggleRe }).click();

    // Single synchronous read right after click captures dataset, localStorage,
    // and aria-pressed in one round-trip. Avoids races with any background
    // navigations the live deployment may issue.
    const state = await page.evaluate(() => ({
      theme: document.documentElement.dataset.theme,
      stored: window.localStorage.getItem("ad_engine_theme"),
      aria: document
        .querySelector(".theme-toggle")
        ?.getAttribute("aria-pressed"),
    }));
    expect(state.theme).toBe(flipped);
    expect(state.stored).toBe(flipped);
    expect(state.aria).toBe(flipped === "dark" ? "true" : "false");
  });

  test("theme is applied synchronously before React mounts (no FOUC)", async ({ page }) => {
    // Pre-seed localStorage so the pre-mount script in index.html has a stored value
    // to honor when the document is first parsed.
    await page.addInitScript(() => {
      window.localStorage.setItem("ad_engine_theme", "dark");
    });
    await page.goto("/");
    const themeAtParseTime = await page.evaluate(
      () => document.documentElement.getAttribute("data-theme"),
    );
    expect(themeAtParseTime).toBe("dark");
  });

  test("loads without console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto("/");
    await page.getByRole("heading", { name: "New brief" }).waitFor();
    expect(errors).toEqual([]);
  });
});

// Flows that need an existing approved campaign (Reuse brief, Cancel edit,
// Regenerate-image confirm guard) are intentionally scoped out of the shell
// smoke suite. They depend on backend fixtures and OpenAI image credits, and
// will land in a follow-up spec once we have a data-seeding helper.
test.fixme("reuse brief copies the selected campaign into the form", () => {});
test.fixme("cancel discards an in-progress variant edit", () => {});
test.fixme("regenerate-image confirm guard blocks the API call when declined", () => {});
