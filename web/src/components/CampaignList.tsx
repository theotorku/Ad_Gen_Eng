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
        {!campaigns.length ? <p className="empty-state">Generate a campaign to populate the dashboard.</p> : null}
      </div>
    </div>
  );
}

export default CampaignList;
