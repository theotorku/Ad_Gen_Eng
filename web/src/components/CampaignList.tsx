import { FileText } from "lucide-react";
import type { CampaignRecord } from "../types";

type CampaignListProps = {
  campaigns: CampaignRecord[];
  selectedCampaignId: string | null;
  onSelect: (campaignId: string) => void;
};

function CampaignList({ campaigns, selectedCampaignId, onSelect }: CampaignListProps) {
  return (
    <div className="campaign-panel">
      <div className="section-marker">
        <span className="num">02·a /</span>
        <h3>Campaigns</h3>
      </div>
      <div className="campaign-list">
        {campaigns.map((campaign) => (
          <button
            key={campaign.id}
            type="button"
            className={campaign.id === selectedCampaignId ? "campaign-row selected" : "campaign-row"}
            onClick={() => onSelect(campaign.id)}
          >
            <div>
              <p className="campaign-title">{campaign.bundle.brief.brand_name}</p>
              <p className="campaign-subtitle">{campaign.bundle.brief.product_name}</p>
            </div>
            <div className="campaign-meta">
              <span className={campaign.status === "approved" ? "status-badge approved" : "status-badge"}>
                {campaign.status}
              </span>
              <span>{campaign.bundle.variants.length} variants</span>
            </div>
          </button>
        ))}
        {!campaigns.length ? (
          <div className="empty-state campaigns-empty">
            <FileText size={28} aria-hidden="true" />
            <p className="empty-state-headline">No campaigns yet</p>
            <p className="empty-state-hint">
              Draft a brief on the left and choose <em>Generate campaign</em> to populate this list.
              <br />
              You can also start from <em>Load sample brief</em> to see a full example bundle.
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default CampaignList;
