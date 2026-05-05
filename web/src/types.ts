export type CampaignBrief = {
  brand_name: string;
  product_name: string;
  objective: string;
  target_audience: string;
  pain_points: string[];
  value_props: string[];
  offer?: string | null;
  tone?: string | null;
  channels: string[];
  constraints: string[];
};

export type CreativePlan = {
  strategy_summary: string;
  audience_promise: string;
  hooks: string[];
  messaging_pillars: string[];
  channel_notes: Record<string, string>;
};

export type AdVariant = {
  channel: string;
  angle: string;
  headline: string;
  primary_text: string;
  cta: string;
  image_prompt: string;
  generated_asset?: GeneratedAsset | null;
  review_notes: string[];
};

export type GeneratedAsset = {
  path: string;
  mime_type: string;
  provider: string;
  prompt: string;
  revised_prompt?: string | null;
};

export type QualitySummary = {
  strengths: string[];
  risks: string[];
};

export type AdBundle = {
  brief: CampaignBrief;
  creative_plan: CreativePlan;
  variants: AdVariant[];
  quality_summary: QualitySummary;
};

export type CampaignStatus = "draft" | "approved";

export type CampaignRecord = {
  id: string;
  organization_id: string;
  created_at: string;
  updated_at: string;
  status: CampaignStatus;
  approval_notes: string | null;
  approved_at: string | null;
  metadata: Record<string, unknown>;
  bundle: AdBundle;
};

export type CampaignListResponse = {
  campaigns: CampaignRecord[];
  count: number;
};
