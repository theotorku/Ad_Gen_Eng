import { CheckCircle2, Sparkles } from "lucide-react";
import type { CampaignRecord } from "../types";
import { formatTimestamp } from "../utils";
import VariantCard from "./VariantCard";

type CampaignDetailProps = {
  campaign: CampaignRecord | null;
  approvalNotes: string;
  onApprovalNotesChange: (value: string) => void;
  onSaveNotes: () => void;
  onApprove: () => void;
};

function CampaignDetail({
  campaign,
  approvalNotes,
  onApprovalNotesChange,
  onSaveNotes,
  onApprove,
}: CampaignDetailProps) {
  if (!campaign) {
    return (
      <div className="detail-panel">
        <div className="empty-detail">
          <Sparkles size={22} />
          <p>Select a campaign on the left to inspect strategy, copy, and approval status.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="detail-panel">
      <div className="detail-header">
        <div>
          <p className="eyebrow">02·b / Selected</p>
          <h3>{campaign.bundle.brief.brand_name}</h3>
          <p className="campaign-objective">{campaign.bundle.brief.objective}</p>
        </div>
        <div className="detail-actions">
          <span className={campaign.status === "approved" ? "status-badge approved" : "status-badge"}>
            {campaign.status}
          </span>
          <button className="ghost-action" type="button" onClick={onSaveNotes}>
            Save notes
          </button>
          <button className="primary-inline" type="button" onClick={onApprove}>
            <CheckCircle2 size={14} />
            Approve
          </button>
        </div>
      </div>

      <div className="detail-columns">
        <section className="detail-section">
          <h4>Strategy</h4>
          <p>{campaign.bundle.creative_plan.strategy_summary}</p>
          <p>{campaign.bundle.creative_plan.audience_promise}</p>
          <ul className="tag-list">
            {campaign.bundle.creative_plan.messaging_pillars.map((pillar) => (
              <li key={pillar}>{pillar}</li>
            ))}
          </ul>
        </section>

        <section className="detail-section">
          <h4>Approval notes</h4>
          <textarea
            rows={5}
            value={approvalNotes}
            onChange={(event) => onApprovalNotesChange(event.target.value)}
          />
          <div className="metric-strip">
            <div>
              <span>Created</span>
              <strong>{formatTimestamp(campaign.created_at)}</strong>
            </div>
            <div>
              <span>Updated</span>
              <strong>{formatTimestamp(campaign.updated_at)}</strong>
            </div>
            <div>
              <span>Approved</span>
              <strong>{campaign.approved_at ? formatTimestamp(campaign.approved_at) : "Pending"}</strong>
            </div>
          </div>
        </section>
      </div>

      <section className="variants-section">
        <div className="section-marker">
          <span className="num">03 /</span>
          <h4>Generated variants</h4>
        </div>
        <div className="variant-grid">
          {campaign.bundle.variants.map((variant) => (
            <VariantCard key={`${variant.channel}-${variant.angle}`} variant={variant} />
          ))}
        </div>
      </section>
    </div>
  );
}

export default CampaignDetail;
