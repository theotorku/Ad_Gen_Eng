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

export const BRIEF_FIELD_LABELS: Record<string, string> = {
  brand_name: "Brand",
  product_name: "Product",
  objective: "Objective",
  target_audience: "Audience",
  pain_points: "Pain points",
  value_props: "Value props",
  offer: "Offer",
  tone: "Tone",
  channels: "Channels",
  constraints: "Constraints",
};

export const EMPTY_FORM: CampaignBrief = {
  brand_name: "",
  product_name: "",
  objective: "",
  target_audience: "",
  pain_points: [],
  value_props: [],
  offer: "",
  tone: "",
  channels: [],
  constraints: [],
};
