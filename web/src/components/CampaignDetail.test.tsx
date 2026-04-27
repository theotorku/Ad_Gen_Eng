import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CampaignDetail from "./CampaignDetail";
import { buildCampaign } from "../test-fixtures";

function renderDetail(overrides: Partial<Parameters<typeof CampaignDetail>[0]> = {}) {
  const props = {
    campaign: buildCampaign(),
    approvalNotes: "",
    onApprovalNotesChange: vi.fn(),
    onSaveNotes: vi.fn(),
    onApprove: vi.fn(),
    ...overrides,
  };
  render(<CampaignDetail {...props} />);
  return props;
}

describe("CampaignDetail", () => {
  it("renders the empty prompt when no campaign is selected", () => {
    render(
      <CampaignDetail
        campaign={null}
        approvalNotes=""
        onApprovalNotesChange={vi.fn()}
        onSaveNotes={vi.fn()}
        onApprove={vi.fn()}
      />,
    );

    expect(screen.getByText(/select a campaign/i)).toBeInTheDocument();
  });

  it("renders strategy, pillars, and at least one variant when a campaign is provided", () => {
    renderDetail();

    expect(screen.getByText("Speak to operators who need throughput.")).toBeInTheDocument();
    expect(screen.getByText("Velocity")).toBeInTheDocument();
    expect(screen.getByText("Ship campaigns in hours, not weeks")).toBeInTheDocument();
  });

  it("calls onApprove when the approve button is clicked", async () => {
    const props = renderDetail();

    await userEvent.click(screen.getByRole("button", { name: /approve/i }));

    expect(props.onApprove).toHaveBeenCalledTimes(1);
  });

  it("calls onSaveNotes when the save notes button is clicked", async () => {
    const props = renderDetail();

    await userEvent.click(screen.getByRole("button", { name: /save notes/i }));

    expect(props.onSaveNotes).toHaveBeenCalledTimes(1);
  });

  it("calls onApprovalNotesChange when the textarea is edited", async () => {
    const props = renderDetail();

    await userEvent.type(screen.getByRole("textbox"), "ok");

    expect(props.onApprovalNotesChange).toHaveBeenCalled();
  });

  it("renders Pending when the campaign has not been approved", () => {
    renderDetail();

    expect(screen.getByText("Pending")).toBeInTheDocument();
  });
});
