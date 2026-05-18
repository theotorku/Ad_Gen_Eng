import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CampaignDetail from "./CampaignDetail";
import { buildCampaign } from "../test-fixtures";

function renderDetail(overrides: Partial<Parameters<typeof CampaignDetail>[0]> = {}) {
  const props = {
    campaign: buildCampaign(),
    approvalNotes: "",
    isSaving: false,
    savingVariantIndex: null,
    generatingImageIndex: null,
    isApproving: false,
    isExporting: false,
    onApprovalNotesChange: vi.fn(),
    onSaveNotes: vi.fn(),
    onSaveVariant: vi.fn(),
    onGenerateVariantImage: vi.fn(),
    onApprove: vi.fn(),
    onExport: vi.fn(),
    onReuseBrief: vi.fn(),
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
        isSaving={false}
        savingVariantIndex={null}
        generatingImageIndex={null}
        isApproving={false}
        isExporting={false}
        onApprovalNotesChange={vi.fn()}
        onSaveNotes={vi.fn()}
        onSaveVariant={vi.fn()}
        onGenerateVariantImage={vi.fn()}
        onApprove={vi.fn()}
        onExport={vi.fn()}
        onReuseBrief={vi.fn()}
      />,
    );

    expect(screen.getByText(/select a campaign/i)).toBeInTheDocument();
  });

  it("calls onReuseBrief when the reuse brief button is clicked", async () => {
    const props = renderDetail();

    await userEvent.click(screen.getByRole("button", { name: /reuse brief/i }));

    expect(props.onReuseBrief).toHaveBeenCalledTimes(1);
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

  it("calls onExport when the export button is clicked", async () => {
    const props = renderDetail();

    await userEvent.click(screen.getByRole("button", { name: /export/i }));

    expect(props.onExport).toHaveBeenCalledTimes(1);
  });

  it("passes image generation requests from variant cards", async () => {
    const props = renderDetail();
    const [generateImageButton] = screen.getAllByRole("button", { name: /generate image/i });
    if (!generateImageButton) {
      throw new Error("Expected at least one generate image button.");
    }

    await userEvent.click(generateImageButton);

    expect(props.onGenerateVariantImage).toHaveBeenCalledWith(0);
  });

  it("calls onApprovalNotesChange when the textarea is edited", async () => {
    const props = renderDetail();

    await userEvent.type(screen.getByRole("textbox"), "ok");

    expect(props.onApprovalNotesChange).toHaveBeenCalled();
  });

  it("disables save notes while saving", () => {
    renderDetail({ isSaving: true });

    expect(screen.getByRole("button", { name: /saving/i })).toBeDisabled();
  });

  it("disables approve while approving", () => {
    renderDetail({ isApproving: true });

    expect(screen.getByRole("button", { name: /approving/i })).toBeDisabled();
  });

  it("disables export while exporting", () => {
    renderDetail({ isExporting: true });

    expect(screen.getByRole("button", { name: /exporting/i })).toBeDisabled();
  });

  it("renders Pending when the campaign has not been approved", () => {
    renderDetail();

    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("hides the approve button once the campaign is approved", () => {
    renderDetail({
      campaign: buildCampaign({ status: "approved", approved_at: "2025-01-15T11:30:00Z" }),
    });

    expect(screen.queryByRole("button", { name: /^approve(d)?$/i })).not.toBeInTheDocument();
    const badge = document.querySelector(".status-badge.approved");
    expect(badge).not.toBeNull();
    expect(badge).toHaveTextContent(/approved/i);
  });
});
