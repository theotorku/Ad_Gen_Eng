import type { AdVariant, CampaignBrief, CampaignRecord } from "./types";

export const sampleBrief: CampaignBrief = {
  brand_name: "Northstar AI",
  product_name: "CampaignPilot",
  objective: "Generate more qualified demo requests",
  target_audience: "B2B marketing teams",
  pain_points: ["slow campaign cycles"],
  value_props: ["faster iteration"],
  offer: "Book a strategy walkthrough",
  tone: "confident",
  channels: ["linkedin", "facebook"],
  constraints: ["Avoid exaggerated claims"],
};

export const sampleVariant: AdVariant = {
  channel: "google_search",
  angle: "demo-request",
  headline: "Ship campaigns in hours, not weeks",
  primary_text: "Generate, review, and approve ad bundles without leaving the workspace.",
  cta: "Book a demo",
  image_prompt: "Studio-lit dashboard with a single accent gradient",
  generated_asset: null,
  image_status: "prompt_only",
  image_error: null,
  review_notes: [],
};

export function buildCampaign(overrides: Partial<CampaignRecord> = {}): CampaignRecord {
  return {
    id: "cmp_123",
    organization_id: "default",
    created_at: "2025-01-15T10:30:00Z",
    updated_at: "2025-01-15T11:00:00Z",
    status: "draft",
    approval_notes: null,
    approved_at: null,
    metadata: {},
    bundle: {
      brief: sampleBrief,
      creative_plan: {
        strategy_summary: "Speak to operators who need throughput.",
        audience_promise: "Ship campaigns faster without losing quality.",
        hooks: ["Cut the cycle"],
        messaging_pillars: ["Velocity", "Clarity", "Confidence"],
        channel_notes: { linkedin: "Lead with credibility" },
      },
      variants: [sampleVariant],
      quality_summary: { strengths: [], risks: [] },
    },
    ...overrides,
  };
}
