import { useState } from "react";
import { Edit3, ImageIcon, RefreshCw, Save } from "lucide-react";
import type { AdVariant } from "../types";
import { apiBaseUrl, formatChannel } from "../utils";

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
  const [draft, setDraft] = useState({
    headline: variant.headline,
    primary_text: variant.primary_text,
    cta: variant.cta,
    image_prompt: variant.image_prompt,
  });

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

  const imageStatus = isGeneratingImage ? "generating" : variant.image_status ?? (variant.generated_asset ? "generated" : "prompt_only");
  const imageButtonLabel =
    imageStatus === "failed" ? "Retry image" : variant.generated_asset ? "Regenerate image" : "Generate image";

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
          onClick={() => onGenerateImage?.(index)}
          disabled={!onGenerateImage || isGeneratingImage}
        >
          {imageStatus === "failed" ? <RefreshCw size={13} /> : <ImageIcon size={13} />}
          {isGeneratingImage ? "Generating" : imageButtonLabel}
        </button>
        {isEditing ? (
          <button className="ghost-action" type="button" onClick={handleSave} disabled={isSaving}>
            <Save size={13} />
            {isSaving ? "Saving" : "Save"}
          </button>
        ) : (
          <button className="ghost-action" type="button" onClick={handleEdit} disabled={!onSave}>
            <Edit3 size={13} />
            Edit
          </button>
        )}
      </div>
      {isEditing ? (
        <div className="variant-editor">
          <label>
            <span>Headline</span>
            <input
              value={draft.headline}
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
          <h5>{variant.headline}</h5>
          {variant.generated_asset ? (
            <img
              className="variant-image"
              src={`${apiBaseUrl()}${variant.generated_asset.path}`}
              alt={variant.headline}
            />
          ) : null}
          <div className={`image-status ${imageStatus}`}>
            <span>{imageStatus.replace("_", " ")}</span>
            {variant.image_error ? <p>{variant.image_error}</p> : null}
          </div>
          <p>{variant.primary_text}</p>
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
