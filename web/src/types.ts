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
  brand_logo?: string | null;
  brand_profile?: string | null;
  service_areas?: string[];
  proof_points?: string[];
  banned_claims?: string[];
};

export type BrandLogoUploadResponse = {
  path: string;
  mime_type: string;
  size: number;
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
  image_status?: "prompt_only" | "generating" | "generated" | "failed";
  image_error?: string | null;
  review_notes: string[];
  review_score?: number | null;
  suggested_fixes?: string[];
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
  scores?: Record<string, number>;
  suggested_fixes?: string[];
};

export type LandingSection = {
  headline: string;
  subheadline: string;
  proof_points: string[];
  cta: string;
  html_snippet: string;
};

export type GenerationJob = {
  job_id: string;
  kind: string;
  status: string;
  provider: string;
  estimated_credits: number;
  target?: string | null;
};

export type AdBundle = {
  brief: CampaignBrief;
  creative_plan: CreativePlan;
  variants: AdVariant[];
  quality_summary: QualitySummary;
  landing_section?: LandingSection | null;
  generation_jobs?: GenerationJob[];
  cost_summary?: Record<string, unknown>;
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

export type UsageSummary = {
  plan: string;
  period: string;
  enforced: boolean;
  usage: { images: number; campaigns: number };
  limits: { images: number | null; campaigns: number | null };
  features: string[];
};
