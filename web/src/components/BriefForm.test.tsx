import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BriefForm from "./BriefForm";
import { sampleBrief } from "../test-fixtures";
import * as api from "../api";

function renderForm(overrides: Partial<Parameters<typeof BriefForm>[0]> = {}) {
  const props = {
    formState: sampleBrief,
    isPending: false,
    onFieldChange: vi.fn(),
    onListFieldChange: vi.fn(),
    onChannelToggle: vi.fn(),
    onSubmit: vi.fn(),
    onBrandLogoChange: vi.fn(),
    ...overrides,
  };
  render(<BriefForm {...props} />);
  return props;
}

describe("BriefForm", () => {
  it("populates inputs from formState", () => {
    renderForm();

    expect(screen.getByDisplayValue("Northstar AI")).toBeInTheDocument();
    expect(screen.getByDisplayValue("CampaignPilot")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Book a strategy walkthrough")).toBeInTheDocument();
  });

  it("calls onFieldChange when the brand input is typed", async () => {
    const props = renderForm();

    const brandInput = screen.getByDisplayValue("Northstar AI");
    await userEvent.type(brandInput, "X");

    expect(props.onFieldChange).toHaveBeenCalledWith("brand_name", expect.any(String));
  });

  it("calls onChannelToggle when a channel segment is clicked", async () => {
    const props = renderForm();

    await userEvent.click(screen.getByRole("button", { name: "Instagram" }));

    expect(props.onChannelToggle).toHaveBeenCalledWith("instagram");
  });

  it("marks selected channels with the active class and aria-pressed", () => {
    renderForm();

    const linkedin = screen.getByRole("button", { name: "LinkedIn" });
    const instagram = screen.getByRole("button", { name: "Instagram" });

    expect(linkedin).toHaveClass("active");
    expect(linkedin).toHaveAttribute("aria-pressed", "true");
    expect(instagram).not.toHaveClass("active");
    expect(instagram).toHaveAttribute("aria-pressed", "false");
  });

  it("groups channel segments with an accessible label", () => {
    renderForm();

    const group = screen.getByRole("group", { name: /channels/i });
    expect(group).toBeInTheDocument();
    expect(group).toContainElement(screen.getByRole("button", { name: "LinkedIn" }));
  });

  it("calls onSubmit when the generate button is clicked", async () => {
    const props = renderForm();

    await userEvent.click(screen.getByRole("button", { name: /generate campaign/i }));

    expect(props.onSubmit).toHaveBeenCalledTimes(1);
  });

  it("disables the generate button while pending", () => {
    renderForm({ isPending: true });

    expect(screen.getByRole("button", { name: /generate campaign/i })).toBeDisabled();
  });

  it("calls onLoadSample when the Load sample brief button is clicked", async () => {
    const onLoadSample = vi.fn();
    renderForm({ onLoadSample });

    await userEvent.click(screen.getByRole("button", { name: /load sample brief/i }));

    expect(onLoadSample).toHaveBeenCalledTimes(1);
  });

  it("calls onReset when the Clear button is clicked", async () => {
    const onReset = vi.fn();
    renderForm({ onReset });

    await userEvent.click(screen.getByRole("button", { name: /^clear$/i }));

    expect(onReset).toHaveBeenCalledTimes(1);
  });

  it("omits the quickstart controls when no handlers are provided", () => {
    renderForm();

    expect(screen.queryByRole("button", { name: /load sample brief/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^clear$/i })).not.toBeInTheDocument();
  });

  it("shows the brand logo upload control by default", () => {
    renderForm();

    expect(screen.getByRole("button", { name: /upload logo/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^remove$/i })).not.toBeInTheDocument();
  });

  it("uploads a selected logo and reports the resulting path", async () => {
    const uploadSpy = vi.spyOn(api, "uploadBrandLogo").mockResolvedValue({
      path: "/brand-logos/abc123.png",
      mime_type: "image/png",
      size: 42,
    });
    const onBrandLogoChange = vi.fn();
    renderForm({ onBrandLogoChange });

    const file = new File(["fake"], "logo.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, file);

    await waitFor(() =>
      expect(onBrandLogoChange).toHaveBeenCalledWith("/brand-logos/abc123.png"),
    );
    expect(uploadSpy).toHaveBeenCalledTimes(1);
    uploadSpy.mockRestore();
  });

  it("shows a remove button and preview when a logo is already attached", async () => {
    vi.spyOn(api, "fetchAssetBlobUrl").mockResolvedValue("blob:preview");
    renderForm({
      formState: { ...sampleBrief, brand_logo: "/brand-logos/abc123.png" },
    });

    expect(screen.getByRole("button", { name: /replace logo/i })).toBeInTheDocument();
    const removeButton = screen.getByRole("button", { name: /^remove$/i });
    expect(removeButton).toBeInTheDocument();

    await waitFor(() => {
      const preview = screen.getByAltText(/brand logo preview/i) as HTMLImageElement;
      expect(preview.src).toContain("blob:preview");
    });
  });

  it("invokes onBrandLogoChange(null) when the remove button is clicked", async () => {
    vi.spyOn(api, "fetchAssetBlobUrl").mockResolvedValue("blob:preview");
    const onBrandLogoChange = vi.fn();
    renderForm({
      formState: { ...sampleBrief, brand_logo: "/brand-logos/abc123.png" },
      onBrandLogoChange,
    });

    await userEvent.click(screen.getByRole("button", { name: /^remove$/i }));

    expect(onBrandLogoChange).toHaveBeenCalledWith(null);
  });
});
