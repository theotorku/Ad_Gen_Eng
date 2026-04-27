import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BriefForm from "./BriefForm";
import { sampleBrief } from "../test-fixtures";

function renderForm(overrides: Partial<Parameters<typeof BriefForm>[0]> = {}) {
  const props = {
    formState: sampleBrief,
    isPending: false,
    onFieldChange: vi.fn(),
    onListFieldChange: vi.fn(),
    onChannelToggle: vi.fn(),
    onSubmit: vi.fn(),
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

  it("marks selected channels with the active class", () => {
    renderForm();

    const linkedin = screen.getByRole("button", { name: "LinkedIn" });
    const instagram = screen.getByRole("button", { name: "Instagram" });

    expect(linkedin).toHaveClass("active");
    expect(instagram).not.toHaveClass("active");
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
});
