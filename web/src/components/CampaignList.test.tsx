import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CampaignList from "./CampaignList";
import { buildCampaign } from "../test-fixtures";

describe("CampaignList", () => {
  it("renders the empty state when no campaigns exist", () => {
    render(<CampaignList campaigns={[]} selectedCampaignId={null} onSelect={vi.fn()} />);

    expect(screen.getByText(/generate a campaign/i)).toBeInTheDocument();
  });

  it("renders one row per campaign with brand and product names", () => {
    const campaigns = [
      buildCampaign({ id: "a" }),
      buildCampaign({ id: "b", bundle: { ...buildCampaign().bundle, brief: { ...buildCampaign().bundle.brief, brand_name: "Acme" } } }),
    ];

    render(<CampaignList campaigns={campaigns} selectedCampaignId={null} onSelect={vi.fn()} />);

    expect(screen.getAllByText("Northstar AI")).toHaveLength(1);
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getAllByText("CampaignPilot").length).toBeGreaterThan(0);
  });

  it("calls onSelect with the campaign id when a row is clicked", async () => {
    const onSelect = vi.fn();
    const campaign = buildCampaign({ id: "cmp_42" });

    render(
      <CampaignList campaigns={[campaign]} selectedCampaignId={null} onSelect={onSelect} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Northstar AI/ }));

    expect(onSelect).toHaveBeenCalledWith("cmp_42");
  });

  it("applies the selected class to the active campaign row", () => {
    const campaigns = [buildCampaign({ id: "a" }), buildCampaign({ id: "b" })];

    render(
      <CampaignList campaigns={campaigns} selectedCampaignId="b" onSelect={vi.fn()} />,
    );

    const rows = screen.getAllByRole("button");
    expect(rows[0]).not.toHaveClass("selected");
    expect(rows[1]).toHaveClass("selected");
  });

  it("renders the approved badge variant for approved campaigns", () => {
    const campaign = buildCampaign({ status: "approved" });

    render(
      <CampaignList campaigns={[campaign]} selectedCampaignId={null} onSelect={vi.fn()} />,
    );

    expect(screen.getByText("approved")).toHaveClass("approved");
  });
});
