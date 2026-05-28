import type {
  AdVariant,
  BrandLogoUploadResponse,
  CampaignBrief,
  CampaignListResponse,
  CampaignRecord,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const ORGANIZATION_ID = import.meta.env.VITE_ORGANIZATION_ID || "default";
const API_KEY = import.meta.env.VITE_API_KEY;

type AuthTokenProvider = () => Promise<string | null>;

let authTokenProvider: AuthTokenProvider | null = null;

export function setAuthTokenProvider(provider: AuthTokenProvider | null): void {
  authTokenProvider = provider;
}

function buildHeaders(
  init?: RequestInit,
  options: { json?: boolean } = { json: true },
  token: string | null = null,
): HeadersInit {
  return {
    ...(options.json ? { "Content-Type": "application/json" } : {}),
    "X-Organization-ID": ORGANIZATION_ID,
    ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init?.headers ?? {}),
  };
}

async function resolveHeaders(
  init?: RequestInit,
  options: { json?: boolean } = { json: true },
): Promise<HeadersInit> {
  if (!authTokenProvider) return buildHeaders(init, options);
  return buildHeaders(init, options, await authTokenProvider());
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = authTokenProvider ? await resolveHeaders(init) : buildHeaders(init);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
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

async function requestText(path: string, init?: RequestInit): Promise<string> {
  const headers = authTokenProvider ? await resolveHeaders(init) : buildHeaders(init);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
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

  return response.text();
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

export async function updateCampaignVariant(
  campaignId: string,
  variantIndex: number,
  payload: Pick<AdVariant, "headline" | "primary_text" | "cta" | "image_prompt">,
): Promise<CampaignRecord> {
  return requestJson<CampaignRecord>(`/campaigns/${campaignId}/variants/${variantIndex}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function generateVariantImage(
  campaignId: string,
  variantIndex: number,
): Promise<CampaignRecord> {
  return requestJson<CampaignRecord>(`/campaigns/${campaignId}/variants/${variantIndex}/generate-image`, {
    method: "POST",
  });
}

export async function exportCampaignText(campaignId: string): Promise<string> {
  return requestText(`/campaigns/${campaignId}/export.txt`);
}

export async function fetchAssetBlobUrl(path: string): Promise<string> {
  const headers = authTokenProvider ? await resolveHeaders() : buildHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers,
  });
  if (!response.ok) {
    throw new Error(`Asset fetch failed with status ${response.status}`);
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export async function uploadBrandLogo(file: File): Promise<BrandLogoUploadResponse> {
  const body = new FormData();
  body.append("file", file);
  const headerOptions = { json: false };
  const headers = authTokenProvider
    ? await resolveHeaders(undefined, headerOptions)
    : buildHeaders(undefined, headerOptions);
  const response = await fetch(`${API_BASE_URL}/assets/brand-logos`, {
    method: "POST",
    headers,
    body,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string;
      error?: string;
    } | null;
    throw new Error(
      payload?.error ?? payload?.detail ?? `Upload failed with status ${response.status}`,
    );
  }
  return (await response.json()) as BrandLogoUploadResponse;
}
