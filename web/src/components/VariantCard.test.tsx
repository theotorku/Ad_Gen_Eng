import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import VariantCard from "./VariantCard";
import { sampleVariant } from "../test-fixtures";

describe("VariantCard", () => {
  it("renders headline, primary text, cta, and image prompt", () => {
    render(<VariantCard variant={sampleVariant} />);

    expect(screen.getByText("Ship campaigns in hours, not weeks")).toBeInTheDocument();
    expect(screen.getByText(/Generate, review, and approve/)).toBeInTheDocument();
    expect(screen.getByText("Book a demo")).toBeInTheDocument();
    expect(screen.getByText("Studio-lit dashboard with a single accent gradient")).toBeInTheDocument();
  });

  it("formats the channel name with title case", () => {
    render(<VariantCard variant={sampleVariant} />);

    expect(screen.getByText("Google Search")).toBeInTheDocument();
  });

  it("does not render an image when generated_asset is null", () => {
    render(<VariantCard variant={sampleVariant} />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("renders the image when generated_asset is present", () => {
    const variant = {
      ...sampleVariant,
      generated_asset: {
        path: "/assets/foo.png",
        mime_type: "image/png",
        provider: "openai_images",
        prompt: "p",
        revised_prompt: null,
      },
    };

    render(<VariantCard variant={variant} />);

    const img = screen.getByRole("img") as HTMLImageElement;
    expect(img.src).toContain("/assets/foo.png");
    expect(img.alt).toBe("Ship campaigns in hours, not weeks");
  });
});
