import { useEffect, useRef, useState } from "react";
import { Check, Copy, Edit3, ImageIcon, RefreshCw, Save, X } from "lucide-react";
import type { AdVariant } from "../types";
import { fetchAssetBlobUrl } from "../api";
import { formatChannel } from "../utils";

function buildVariantClipboardText(variant: AdVariant): string {
  const lines = [
    `${formatChannel(variant.channel)} — ${variant.cta}`,
    "",
    variant.headline,
    "",
    variant.primary_text,
    "",
    "Image prompt:",
    variant.image_prompt,
  ];
  return lines.join("\n");
}

type VariantCardProps = {
  variant: AdVariant;
  index?: number;
  isSaving?: boolean;
  isGeneratingImage?: boolean;
  onSave?: (
    index: number,
    payload: Pick<AdVariant, "headline" | "primary_text" | "cta" | "image_prompt">,
  ) => void;
  onGenerateImage?: (index: number) => void;
};

function VariantCard({
  variant,
  index = 0,
  isSaving = false,
  isGeneratingImage = false,
  onSave,
  onGenerateImage,
}: VariantCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [regenerationCount, setRegenerationCount] = useState(0);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const copyResetTimerRef = useRef<number | null>(null);
  const [draft, setDraft] = useState({
    headline: variant.headline,
    primary_text: variant.primary_text,
    cta: variant.cta,
    image_prompt: variant.image_prompt,
  });

  useEffect(() => {
    return () => {
      if (copyResetTimerRef.current !== null) {
        window.clearTimeout(copyResetTimerRef.current);
      }
    };
  }, []);

  async function handleCopyVariant() {
    const text = buildVariantClipboardText(variant);
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        throw new Error("Clipboard API unavailable");
      }
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
    if (copyResetTimerRef.current !== null) {
      window.clearTimeout(copyResetTimerRef.current);
    }
    copyResetTimerRef.current = window.setTimeout(() => setCopyState("idle"), 2000);
  }

  const assetPath = variant.generated_asset?.path ?? null;
  useEffect(() => {
    if (!assetPath) {
      setImageUrl(null);
      return;
    }
    let cancelled = false;
    let createdUrl: string | null = null;
    fetchAssetBlobUrl(assetPath)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        createdUrl = url;
        setImageUrl(url);
      })
      .catch(() => {
        if (!cancelled) setImageUrl(null);
      });
    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [assetPath]);

  function handleEdit() {
    setDraft({
      headline: variant.headline,
      primary_text: variant.primary_text,
      cta: variant.cta,
      image_prompt: variant.image_prompt,
    });
    setIsEditing(true);
  }

  function handleSave() {
    onSave?.(index, draft);
    setIsEditing(false);
  }

  function handleCancelEdit() {
    setDraft({
      headline: variant.headline,
      primary_text: variant.primary_text,
      cta: variant.cta,
      image_prompt: variant.image_prompt,
    });
    setIsEditing(false);
  }

  const imageStatus = isGeneratingImage ? "generating" : variant.image_status ?? (variant.generated_asset ? "generated" : "prompt_only");
  const imageButtonLabel =
    imageStatus === "failed" ? "Retry image" : variant.generated_asset ? "Regenerate image" : "Generate image";
  const hasExistingAsset = Boolean(variant.generated_asset) && imageStatus !== "failed";

  function handleGenerateImageClick() {
    if (!onGenerateImage) return;
    if (hasExistingAsset) {
      const confirmed = window.confirm(
        "Regenerate this image? This will use another OpenAI image credit and replace the current asset.",
      );
      if (!confirmed) return;
    }
    setRegenerationCount((current) => (hasExistingAsset ? current + 1 : current));
    onGenerateImage(index);
  }

  return (
    <article className="variant-item">
      <div className="variant-head">
        <span className="channel-chip">{formatChannel(variant.channel)}</span>
        <span>{variant.cta}</span>
      </div>
      <div className="variant-actions">
        <button
          className="ghost-action"
          type="button"
          onClick={handleGenerateImageClick}
          disabled={!onGenerateImage || isGeneratingImage}
        >
          {imageStatus === "failed" ? <RefreshCw size={13} /> : <ImageIcon size={13} />}
          {isGeneratingImage ? "Generating" : imageButtonLabel}
        </button>
        {isEditing ? (
          <>
            <button
              className="ghost-action"
              type="button"
              onClick={handleCancelEdit}
              disabled={isSaving}
            >
              <X size={13} />
              Cancel
            </button>
            <button className="ghost-action" type="button" onClick={handleSave} disabled={isSaving}>
              <Save size={13} />
              {isSaving ? "Saving" : "Save"}
            </button>
          </>
        ) : (
          <>
            <button
              className="ghost-action"
              type="button"
              onClick={() => void handleCopyVariant()}
              title="Copy this variant as plain text"
            >
              {copyState === "copied" ? <Check size={13} /> : <Copy size={13} />}
              {copyState === "copied" ? "Copied" : copyState === "failed" ? "Copy failed" : "Copy"}
            </button>
            <button className="ghost-action" type="button" onClick={handleEdit} disabled={!onSave}>
              <Edit3 size={13} />
              Edit
            </button>
          </>
        )}
      </div>
      {onGenerateImage && !isEditing ? (
        <p className="image-cost-hint">
          <span>Each image generation uses 1 OpenAI image credit.</span>
          {regenerationCount > 0 ? (
            <span className="regen-count">Regenerated {regenerationCount}× this session</span>
          ) : null}
        </p>
      ) : null}
      {isEditing ? (
        <div className="variant-editor">
          <label>
            <span>Headline</span>
            <textarea
              rows={2}
              value={draft.headline}
              title={draft.headline}
              onChange={(event) => setDraft((current) => ({ ...current, headline: event.target.value }))}
            />
          </label>
          <label>
            <span>Primary text</span>
            <textarea
              rows={4}
              value={draft.primary_text}
              onChange={(event) =>
                setDraft((current) => ({ ...current, primary_text: event.target.value }))
              }
            />
          </label>
          <label>
            <span>CTA</span>
            <input
              value={draft.cta}
              onChange={(event) => setDraft((current) => ({ ...current, cta: event.target.value }))}
            />
          </label>
          <label>
            <span>Image prompt</span>
            <textarea
              rows={5}
              value={draft.image_prompt}
              onChange={(event) =>
                setDraft((current) => ({ ...current, image_prompt: event.target.value }))
              }
            />
          </label>
        </div>
      ) : (
        <>
          <h5 title={variant.headline}>{variant.headline}</h5>
          {typeof variant.review_score === "number" ? (
            <div className="review-score">
              <span>Review score</span>
              <strong>{variant.review_score}</strong>
            </div>
          ) : null}
          {variant.generated_asset && imageUrl ? (
            <img
              className="variant-image"
              src={imageUrl}
              alt={variant.headline}
            />
          ) : null}
          <div className={`image-status ${imageStatus}`}>
            <span>{imageStatus.replace("_", " ")}</span>
            {variant.image_error ? <p>{variant.image_error}</p> : null}
          </div>
          <p>{variant.primary_text}</p>
          {variant.review_notes.length || variant.suggested_fixes?.length ? (
            <div className="prompt-block">
              <span>Review notes</span>
              {[...variant.review_notes, ...(variant.suggested_fixes ?? [])].map((note) => (
                <p key={note}>{note}</p>
              ))}
            </div>
          ) : null}
          <div className="prompt-block">
            <span>Image prompt</span>
            <p>{variant.image_prompt}</p>
          </div>
        </>
      )}
    </article>
  );
}

export default VariantCard;
