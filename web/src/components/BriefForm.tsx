import { Send } from "lucide-react";
import type { CampaignBrief } from "../types";
import { CHANNEL_OPTIONS } from "../constants";

type ListField = "pain_points" | "value_props" | "constraints";

type BriefFormProps = {
  formState: CampaignBrief;
  isPending: boolean;
  onFieldChange: (field: keyof CampaignBrief, value: string) => void;
  onListFieldChange: (field: ListField, value: string) => void;
  onChannelToggle: (channel: string) => void;
  onSubmit: () => void;
};

function BriefForm({
  formState,
  isPending,
  onFieldChange,
  onListFieldChange,
  onChannelToggle,
  onSubmit,
}: BriefFormProps) {
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

        <label>
          <span>Brand</span>
          <input
            value={formState.brand_name}
            onChange={(event) => onFieldChange("brand_name", event.target.value)}
          />
        </label>

        <label>
          <span>Product</span>
          <input
            value={formState.product_name}
            onChange={(event) => onFieldChange("product_name", event.target.value)}
          />
        </label>

        <label>
          <span>Objective</span>
          <input
            value={formState.objective}
            onChange={(event) => onFieldChange("objective", event.target.value)}
          />
        </label>

        <label>
          <span>Audience</span>
          <textarea
            rows={3}
            value={formState.target_audience}
            onChange={(event) => onFieldChange("target_audience", event.target.value)}
          />
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

        <div>
          <span className="field-label">Channels</span>
          <div className="segmented-control">
            {CHANNEL_OPTIONS.map((channel) => {
              const selected = formState.channels.includes(channel.value);
              return (
                <button
                  key={channel.value}
                  type="button"
                  className={selected ? "segment active" : "segment"}
                  onClick={() => onChannelToggle(channel.value)}
                >
                  {channel.label}
                </button>
              );
            })}
          </div>
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
