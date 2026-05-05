import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { createCampaign, fetchCampaigns } from "./api";
import { buildCampaign } from "./test-fixtures";

vi.mock("./api", () => ({
  approveCampaign: vi.fn(),
  createCampaign: vi.fn(),
  exportCampaignText: vi.fn(),
  fetchCampaign: vi.fn(),
  fetchCampaigns: vi.fn(),
  updateCampaign: vi.fn(),
  updateCampaignVariant: vi.fn(),
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

describe("App", () => {
  beforeEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
    vi.clearAllMocks();
  });

  it("locks campaign creation while the request is in flight", async () => {
    const user = userEvent.setup();
    const createdCampaign = buildCampaign({ id: "cmp_created" });
    const creation = deferred<typeof createdCampaign>();

    vi.mocked(fetchCampaigns)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([createdCampaign]);
    vi.mocked(createCampaign).mockReturnValue(creation.promise);

    render(<App />);

    const generateButton = await screen.findByRole("button", { name: /generate campaign/i });
    await user.click(generateButton);
    await user.click(generateButton);

    expect(createCampaign).toHaveBeenCalledTimes(1);
    expect(generateButton).toBeDisabled();

    creation.resolve(createdCampaign);

    await waitFor(() => {
      expect(screen.getByText("Campaign generated")).toBeInTheDocument();
    });
  });

  it("toggles dark mode and persists the preference", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchCampaigns).mockResolvedValue([]);

    render(<App />);

    const themeButton = await screen.findByRole("button", { name: /dark mode/i });
    await user.click(themeButton);

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem("ad_engine_theme")).toBe("dark");
    expect(screen.getByRole("button", { name: /light mode/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
