import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import VariantCard from "./VariantCard";
import { sampleVariant } from "../test-fixtures";

function fakeImageResponse(): Response {
  return {
    ok: true,
    status: 200,
    blob: async () => new Blob(["image-bytes"], { type: "image/png" }),
  } as unknown as Response;
}

describe("VariantCard", () => {
  beforeEach(() => {
    let counter = 0;
    vi.stubGlobal("fetch", vi.fn(async () => fakeImageResponse()));
    vi.spyOn(URL, "createObjectURL").mockImplementation(() => `blob:mock-url-${++counter}`);
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

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

  it("renders the image as an authenticated blob when generated_asset is present", async () => {
    const variant = {
      ...sampleVariant,
      generated_asset: {
        path: "/generated-assets/foo.png",
        mime_type: "image/png",
        provider: "openai_images",
        prompt: "p",
        revised_prompt: null,
      },
    };

    render(<VariantCard variant={variant} />);

    const img = (await screen.findByRole("img")) as HTMLImageElement;
    expect(img.src).toBe("blob:mock-url-1");
    expect(img.alt).toBe("Ship campaigns in hours, not weeks");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/generated-assets/foo.png"),
      expect.objectContaining({
        headers: expect.objectContaining({ "X-Organization-ID": "default" }),
      }),
    );
  });

  it("does not render an image while the blob fetch is in flight", async () => {
    const variant = {
      ...sampleVariant,
      generated_asset: {
        path: "/generated-assets/bar.png",
        mime_type: "image/png",
        provider: "openai_images",
        prompt: "p",
        revised_prompt: null,
      },
    };

    let resolveFetch: (response: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            resolveFetch = resolve;
          }),
      ),
    );

    render(<VariantCard variant={variant} />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();

    resolveFetch(fakeImageResponse());
    await waitFor(() => expect(screen.getByRole("img")).toBeInTheDocument());
  });

  it("edits and saves variant copy", async () => {
    const onSave = vi.fn();
    render(<VariantCard variant={sampleVariant} index={2} onSave={onSave} />);

    await userEvent.click(screen.getByRole("button", { name: /edit/i }));
    await userEvent.clear(screen.getByLabelText(/headline/i));
    await userEvent.type(screen.getByLabelText(/headline/i), "New headline");
    await userEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(onSave).toHaveBeenCalledWith(
      2,
      expect.objectContaining({ headline: "New headline" }),
    );
  });

  it("discards an in-progress edit when Cancel is clicked", async () => {
    const onSave = vi.fn();
    render(<VariantCard variant={sampleVariant} index={2} onSave={onSave} />);

    await userEvent.click(screen.getByRole("button", { name: /edit/i }));
    await userEvent.clear(screen.getByLabelText(/headline/i));
    await userEvent.type(screen.getByLabelText(/headline/i), "Throwaway headline");
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(onSave).not.toHaveBeenCalled();
    expect(screen.queryByLabelText(/headline/i)).not.toBeInTheDocument();
    expect(screen.getByText(sampleVariant.headline)).toBeInTheDocument();
  });

  it("requests image generation for a variant", async () => {
    const onGenerateImage = vi.fn();
    render(<VariantCard variant={sampleVariant} index={3} onGenerateImage={onGenerateImage} />);

    await userEvent.click(screen.getByRole("button", { name: /generate image/i }));

    expect(onGenerateImage).toHaveBeenCalledWith(3);
  });

  it("confirms before regenerating an existing image and surfaces a regen count", async () => {
    const onGenerateImage = vi.fn();
    const variant = {
      ...sampleVariant,
      generated_asset: {
        path: "/generated-assets/foo.png",
        mime_type: "image/png",
        provider: "openai_images",
        prompt: "p",
        revised_prompt: null,
      },
    };
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<VariantCard variant={variant} index={4} onGenerateImage={onGenerateImage} />);

    await userEvent.click(screen.getByRole("button", { name: /regenerate image/i }));
    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(onGenerateImage).not.toHaveBeenCalled();
    expect(screen.queryByText(/Regenerated/)).not.toBeInTheDocument();

    confirmSpy.mockReturnValue(true);
    await userEvent.click(screen.getByRole("button", { name: /regenerate image/i }));
    expect(onGenerateImage).toHaveBeenCalledWith(4);
    expect(screen.getByText(/Regenerated 1× this session/)).toBeInTheDocument();
  });

  it("shows the image cost hint when generation is enabled", () => {
    render(<VariantCard variant={sampleVariant} onGenerateImage={vi.fn()} />);

    expect(
      screen.getByText(/Each image generation uses 1 OpenAI image credit/i),
    ).toBeInTheDocument();
  });

  it("shows retry state when image generation failed", () => {
    render(
      <VariantCard
        variant={{
          ...sampleVariant,
          image_status: "failed",
          image_error: "Provider timed out.",
        }}
      />,
    );

    expect(screen.getByText("failed")).toBeInTheDocument();
    expect(screen.getByText("Provider timed out.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry image/i })).toBeInTheDocument();
  });
});
