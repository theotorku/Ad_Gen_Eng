import type { CampaignBrief } from "./types";

export const CHANNEL_OPTIONS = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "facebook", label: "Facebook" },
  { value: "instagram", label: "Instagram" },
  { value: "google_search", label: "Google Search" },
] as const;

export const SAMPLE_FORM: CampaignBrief = {
  brand_name: "Northstar AI",
  product_name: "CampaignPilot",
  objective: "Generate more qualified demo requests",
  target_audience: "B2B marketing teams at growth-stage SaaS companies",
  pain_points: ["slow campaign production cycles", "generic creative that underperforms"],
  value_props: ["faster ad iteration", "clearer campaign strategy", "less manual copy drafting"],
  offer: "Book a free strategy walkthrough",
  tone: "confident",
  channels: ["linkedin", "facebook", "google_search"],
  constraints: ["Avoid exaggerated performance claims"],
};
