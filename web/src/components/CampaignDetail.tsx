import { CheckCircle2, ClipboardCopy, Download, Sparkles } from "lucide-react";
import type { AdVariant, CampaignRecord } from "../types";
import { formatTimestamp } from "../utils";
import VariantCard from "./VariantCard";

type CampaignDetailProps = {
  campaign: CampaignRecord | null;
  approvalNotes: string;
  isSaving: boolean;
  savingVariantIndex: number | null;
  generatingImageIndex: number | null;
  isApproving: boolean;
  isExporting: boolean;
  onApprovalNotesChange: (value: string) => void;
  onSaveNotes: () => void;
  onSaveVariant: (
    index: number,
    payload: Pick<AdVariant, "headline" | "primary_text" | "cta" | "image_prompt">,
  ) => void;
  onGenerateVariantImage: (index: number) => void;
  onApprove: () => void;
  onExport: () => void;
  onReuseBrief: () => void;
};

function CampaignDetail({
  campaign,
  approvalNotes,
  isSaving,
  savingVariantIndex,
  generatingImageIndex,
  isApproving,
  isExporting,
  onApprovalNotesChange,
  onSaveNotes,
  onSaveVariant,
  onGenerateVariantImage,
  onApprove,
  onExport,
  onReuseBrief,
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
            {campaign.status === "approved" ? (
              <>
                <CheckCircle2 size={12} />
                Approved
              </>
            ) : (
              campaign.status
            )}
          </span>
          <button className="ghost-action" type="button" onClick={onSaveNotes} disabled={isSaving}>
            {isSaving ? "Saving" : "Save notes"}
          </button>
          <button
            className="ghost-action"
            type="button"
            onClick={onReuseBrief}
            title="Reuse this brief in the New Brief form"
          >
            <ClipboardCopy size={14} />
            Reuse brief
          </button>
          <button className="ghost-action" type="button" onClick={onExport} disabled={isExporting}>
            <Download size={14} />
            {isExporting ? "Exporting" : "Export"}
          </button>
          {campaign.status !== "approved" ? (
            <button
              className="primary-inline"
              type="button"
              onClick={onApprove}
              disabled={isApproving}
            >
              <CheckCircle2 size={14} />
              {isApproving ? "Approving" : "Approve"}
            </button>
          ) : null}
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

      <div className="detail-columns">
        <section className="detail-section">
          <h4>Quality gate</h4>
          <div className="metric-strip">
            <div>
              <span>Avg score</span>
              <strong>
                {campaign.bundle.quality_summary.scores?.average_variant_score ?? "N/A"}
              </strong>
            </div>
            <div>
              <span>Checks</span>
              <strong>{campaign.bundle.quality_summary.risks.length}</strong>
            </div>
          </div>
          <ul className="tag-list">
            {campaign.bundle.quality_summary.risks.map((risk) => (
              <li key={risk}>{risk}</li>
            ))}
          </ul>
          {campaign.bundle.quality_summary.suggested_fixes?.length ? (
            <ul className="fix-list">
              {campaign.bundle.quality_summary.suggested_fixes.map((fix) => (
                <li key={fix}>{fix}</li>
              ))}
            </ul>
          ) : null}
        </section>

        {campaign.bundle.landing_section ? (
          <section className="detail-section">
            <h4>Landing section</h4>
            <p>{campaign.bundle.landing_section.headline}</p>
            <p>{campaign.bundle.landing_section.subheadline}</p>
            <ul className="tag-list">
              {campaign.bundle.landing_section.proof_points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
            <pre className="snippet-preview">{campaign.bundle.landing_section.html_snippet}</pre>
          </section>
        ) : null}
      </div>

      <section className="variants-section">
        <div className="section-marker">
          <span className="num">03 /</span>
          <h4>Generated variants</h4>
        </div>
        <div className="variant-grid">
          {campaign.bundle.variants.map((variant, index) => (
            <VariantCard
              key={`${variant.channel}-${variant.angle}`}
              variant={variant}
              index={index}
              isSaving={savingVariantIndex === index}
              isGeneratingImage={generatingImageIndex === index}
              onSave={onSaveVariant}
              onGenerateImage={onGenerateVariantImage}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

export default CampaignDetail;
