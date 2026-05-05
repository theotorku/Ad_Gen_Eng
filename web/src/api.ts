import type { CampaignBrief, CampaignListResponse, CampaignRecord } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const ORGANIZATION_ID = import.meta.env.VITE_ORGANIZATION_ID ?? "default";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Organization-ID": ORGANIZATION_ID,
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string;
      error?: string;
    } | null;
    throw new Error(
      payload?.error ?? payload?.detail ?? `Request failed with status ${response.status}`,
    );
  }

  return (await response.json()) as T;
}

export async function fetchCampaigns(): Promise<CampaignRecord[]> {
  const payload = await requestJson<CampaignListResponse>("/campaigns");
  return payload.campaigns;
}

export async function fetchCampaign(campaignId: string): Promise<CampaignRecord> {
  return requestJson<CampaignRecord>(`/campaigns/${campaignId}`);
}

export async function createCampaign(brief: CampaignBrief): Promise<CampaignRecord> {
  return requestJson<CampaignRecord>("/bundles", {
    method: "POST",
    body: JSON.stringify(brief),
  });
}

export async function updateCampaign(
  campaignId: string,
  payload: {
    status?: "draft" | "approved";
    approval_notes?: string;
    metadata?: Record<string, unknown>;
  },
): Promise<CampaignRecord> {
  return requestJson<CampaignRecord>(`/campaigns/${campaignId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function approveCampaign(campaignId: string, approvalNotes: string): Promise<CampaignRecord> {
  return requestJson<CampaignRecord>(`/campaigns/${campaignId}/approve`, {
    method: "POST",
    body: JSON.stringify({ approval_notes: approvalNotes }),
  });
}
