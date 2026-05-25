import { useEffect, useRef, useState } from "react";
import { ImagePlus, RotateCcw, Send, Sparkles, X } from "lucide-react";
import type { CampaignBrief } from "../types";
import { fetchAssetBlobUrl, uploadBrandLogo } from "../api";
import {
  BRAND_LOGO_ACCEPT,
  BRAND_LOGO_MAX_BYTES,
  CHANNEL_OPTIONS,
} from "../constants";

type ListField = "pain_points" | "value_props" | "constraints";

type BriefFormProps = {
  formState: CampaignBrief;
  isPending: boolean;
  briefErrors?: Partial<Record<keyof CampaignBrief, string>>;
  onFieldChange: (field: keyof CampaignBrief, value: string) => void;
  onListFieldChange: (field: ListField, value: string) => void;
  onChannelToggle: (channel: string) => void;
  onSubmit: () => void;
  onLoadSample?: () => void;
  onReset?: () => void;
  onBrandLogoChange: (path: string | null) => void;
};

function BriefForm({
  formState,
  isPending,
  briefErrors = {},
  onFieldChange,
  onListFieldChange,
  onChannelToggle,
  onSubmit,
  onLoadSample,
  onReset,
  onBrandLogoChange,
}: BriefFormProps) {
  const errorFor = (field: keyof CampaignBrief) => briefErrors[field];
  const fieldClass = (field: keyof CampaignBrief) =>
    errorFor(field) ? "field has-error" : "field";

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [logoUploading, setLogoUploading] = useState(false);
  const [logoError, setLogoError] = useState<string | null>(null);

  useEffect(() => {
    let revokedUrl: string | null = null;
    let cancelled = false;
    if (!formState.brand_logo) {
      setLogoPreview(null);
      return;
    }
    void fetchAssetBlobUrl(formState.brand_logo)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        revokedUrl = url;
        setLogoPreview(url);
      })
      .catch(() => {
        if (!cancelled) setLogoPreview(null);
      });
    return () => {
      cancelled = true;
      if (revokedUrl) URL.revokeObjectURL(revokedUrl);
    };
  }, [formState.brand_logo]);

  async function handleLogoSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > BRAND_LOGO_MAX_BYTES) {
      setLogoError("Logo must be 2 MB or smaller.");
      return;
    }
    setLogoUploading(true);
    setLogoError(null);
    try {
      const result = await uploadBrandLogo(file);
      onBrandLogoChange(result.path);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Logo upload failed.";
      setLogoError(message);
    } finally {
      setLogoUploading(false);
    }
  }

  function handleRemoveLogo() {
    setLogoError(null);
    onBrandLogoChange(null);
  }
  function renderError(field: keyof CampaignBrief) {
    const message = errorFor(field);
    if (!message) return null;
    return (
      <span className="field-error" role="alert">
        {message}
      </span>
    );
  }
  return (
    <aside className="left-rail">
      <div className="rail-header">
        <div className="brand-lockup">
          <h1 className="wordmark">
            Ad<span className="slash">/</span>Gen<br />
            <em>Engine</em>
          </h1>
        </div>
        <div className="edition-line">
          <span>Vol.&nbsp;01</span>
          <span>Studio Edition</span>
        </div>
        <p className="rail-copy">
          A workbench for campaign-ready concepts &mdash; draft, review, and ship without
          leaving the page.
        </p>
      </div>

      <section className="form-section">
        <div className="section-marker">
          <span className="num">01 /</span>
          <h2>New brief</h2>
        </div>
        <p className="form-hint">
          Draft a fresh brief here. Selecting a campaign on the right is for review and
          does not load its brief back into this form.
        </p>
        {(onLoadSample || onReset) && (
          <div className="form-quickstart">
            {onLoadSample ? (
              <button
                className="ghost-action"
                type="button"
                onClick={onLoadSample}
                disabled={isPending}
              >
                <Sparkles size={12} />
                Load sample brief
              </button>
            ) : null}
            {onReset ? (
              <button
                className="ghost-action"
                type="button"
                onClick={onReset}
                disabled={isPending}
              >
                <RotateCcw size={12} />
                Clear
              </button>
            ) : null}
          </div>
        )}

        <label className={fieldClass("brand_name")}>
          <span>
            Brand<span className="required-mark" aria-hidden="true">*</span>
          </span>
          <input
            value={formState.brand_name}
            aria-invalid={Boolean(errorFor("brand_name"))}
            onChange={(event) => onFieldChange("brand_name", event.target.value)}
          />
          {renderError("brand_name")}
        </label>

        <label className={fieldClass("product_name")}>
          <span>
            Product<span className="required-mark" aria-hidden="true">*</span>
          </span>
          <input
            value={formState.product_name}
            title={formState.product_name}
            aria-invalid={Boolean(errorFor("product_name"))}
            onChange={(event) => onFieldChange("product_name", event.target.value)}
          />
          {renderError("product_name")}
        </label>

        <label className={fieldClass("objective")}>
          <span>
            Objective<span className="required-mark" aria-hidden="true">*</span>
          </span>
          <input
            value={formState.objective}
            title={formState.objective}
            aria-invalid={Boolean(errorFor("objective"))}
            onChange={(event) => onFieldChange("objective", event.target.value)}
          />
          {renderError("objective")}
        </label>

        <label className={fieldClass("target_audience")}>
          <span>
            Audience<span className="required-mark" aria-hidden="true">*</span>
          </span>
          <textarea
            rows={3}
            value={formState.target_audience}
            aria-invalid={Boolean(errorFor("target_audience"))}
            onChange={(event) => onFieldChange("target_audience", event.target.value)}
          />
          {renderError("target_audience")}
        </label>

        <label>
          <span>Pain points</span>
          <textarea
            rows={4}
            value={formState.pain_points.join("\n")}
            onChange={(event) => onListFieldChange("pain_points", event.target.value)}
          />
        </label>

        <label>
          <span>Value props</span>
          <textarea
            rows={4}
            value={formState.value_props.join("\n")}
            onChange={(event) => onListFieldChange("value_props", event.target.value)}
          />
        </label>

        <div className="field-grid">
          <label>
            <span>Offer</span>
            <input
              value={formState.offer ?? ""}
              title={formState.offer ?? ""}
              onChange={(event) => onFieldChange("offer", event.target.value)}
            />
          </label>

          <label>
            <span>Tone</span>
            <input
              value={formState.tone ?? ""}
              onChange={(event) => onFieldChange("tone", event.target.value)}
            />
          </label>
        </div>

        <label>
          <span>Constraints</span>
          <textarea
            rows={3}
            value={formState.constraints.join("\n")}
            onChange={(event) => onListFieldChange("constraints", event.target.value)}
          />
        </label>

        <div className="field brand-logo-field">
          <span className="field-label">Brand logo</span>
          <p className="form-hint">
            PNG, JPEG, or WEBP up to 2 MB. The logo is composited onto the
            bottom-right corner of every generated image for visual consistency.
          </p>
          <div className="brand-logo-row">
            {logoPreview ? (
              <img
                src={logoPreview}
                alt="Uploaded brand logo preview"
                className="brand-logo-preview"
              />
            ) : (
              <div className="brand-logo-placeholder" aria-hidden="true">
                <ImagePlus size={18} />
              </div>
            )}
            <div className="brand-logo-actions">
              <input
                ref={fileInputRef}
                type="file"
                accept={BRAND_LOGO_ACCEPT}
                hidden
                onChange={handleLogoSelect}
              />
              <button
                type="button"
                className="ghost-action"
                disabled={isPending || logoUploading}
                onClick={() => fileInputRef.current?.click()}
              >
                <ImagePlus size={12} />
                {formState.brand_logo ? "Replace logo" : "Upload logo"}
              </button>
              {formState.brand_logo ? (
                <button
                  type="button"
                  className="ghost-action"
                  disabled={isPending || logoUploading}
                  onClick={handleRemoveLogo}
                >
                  <X size={12} />
                  Remove
                </button>
              ) : null}
            </div>
          </div>
          {logoUploading ? (
            <span className="field-hint">Uploading logo&hellip;</span>
          ) : null}
          {logoError ? (
            <span className="field-error" role="alert">
              {logoError}
            </span>
          ) : null}
        </div>

        <div className={fieldClass("channels")}>
          <span className="field-label" id="channels-label">
            Channels<span className="required-mark" aria-hidden="true">*</span>
          </span>
          <div
            className={
              errorFor("channels")
                ? "segmented-control has-error"
                : "segmented-control"
            }
            role="group"
            aria-labelledby="channels-label"
            aria-invalid={Boolean(errorFor("channels"))}
          >
            {CHANNEL_OPTIONS.map((channel) => {
              const selected = formState.channels.includes(channel.value);
              return (
                <button
                  key={channel.value}
                  type="button"
                  className={selected ? "segment active" : "segment"}
                  onClick={() => onChannelToggle(channel.value)}
                  aria-pressed={selected}
                >
                  {channel.label}
                </button>
              );
            })}
          </div>
          {renderError("channels")}
        </div>

        <button className="primary-action" type="button" onClick={onSubmit} disabled={isPending}>
          <Send size={14} />
          Generate campaign
        </button>
      </section>
    </aside>
  );
}

export default BriefForm;
