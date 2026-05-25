import { useEffect, useMemo, useState, useTransition } from "react";
import { LoaderCircle, Moon, RefreshCw, Sun } from "lucide-react";
import {
  approveCampaign,
  createCampaign,
  exportCampaignText,
  fetchCampaign,
  fetchCampaigns,
  generateVariantImage,
  updateCampaign,
  updateCampaignVariant,
} from "./api";
import type { AdVariant, CampaignBrief, CampaignRecord } from "./types";
import { BRIEF_FIELD_LABELS, EMPTY_FORM, SAMPLE_FORM } from "./constants";
import BriefForm from "./components/BriefForm";
import CampaignList from "./components/CampaignList";
import CampaignDetail from "./components/CampaignDetail";

type ThemeMode = "light" | "dark";

const THEME_STORAGE_KEY = "ad_engine_theme";
const FAILURE_STATUS_RE = /failed/i;
const IDLE_STATUS = "Ready";

function humanizeBriefError(message: string): string {
  // The API returns raw column names (e.g. "Missing required brief fields:
  // brand_name, product_name"). Replace any whole-word key with its label.
  return message.replace(/\b([a-z_]+)\b/g, (match) =>
    Object.prototype.hasOwnProperty.call(BRIEF_FIELD_LABELS, match)
      ? BRIEF_FIELD_LABELS[match]
      : match,
  );
}

type BriefErrors = Partial<Record<keyof CampaignBrief, string>>;

function validateBrief(brief: CampaignBrief): BriefErrors {
  const errors: BriefErrors = {};
  if (!brief.brand_name.trim()) errors.brand_name = "Brand is required.";
  if (!brief.product_name.trim()) errors.product_name = "Product is required.";
  if (!brief.objective.trim()) errors.objective = "Objective is required.";
  if (!brief.target_audience.trim())
    errors.target_audience = "Audience is required.";
  if (brief.channels.length === 0)
    errors.channels = "Select at least one channel.";
  return errors;
}

function isBriefDirty(brief: CampaignBrief): boolean {
  if (brief.brand_name.trim()) return true;
  if (brief.product_name.trim()) return true;
  if (brief.objective.trim()) return true;
  if (brief.target_audience.trim()) return true;
  if (brief.offer?.trim()) return true;
  if (brief.tone?.trim()) return true;
  if (brief.channels.length > 0) return true;
  if (brief.pain_points.length > 0) return true;
  if (brief.value_props.length > 0) return true;
  if (brief.constraints.length > 0) return true;
  return false;
}

function getInitialTheme(): ThemeMode {
  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (storedTheme === "light" || storedTheme === "dark") {
    return storedTheme;
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function App() {
  const [campaigns, setCampaigns] = useState<CampaignRecord[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [formState, setFormState] = useState<CampaignBrief>(EMPTY_FORM);
  const [approvalNotes, setApprovalNotes] = useState("");
  const [statusMessage, setStatusMessage] = useState("Loading campaigns");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [briefErrors, setBriefErrors] = useState<BriefErrors>({});
  const [isCreating, setIsCreating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [savingVariantIndex, setSavingVariantIndex] = useState<number | null>(null);
  const [generatingImageIndex, setGeneratingImageIndex] = useState<number | null>(null);
  const [isApproving, setIsApproving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme);
  const [isPending, startTransition] = useTransition();
  const isWorking =
    isPending ||
    isCreating ||
    isSaving ||
    isApproving ||
    savingVariantIndex !== null ||
    generatingImageIndex !== null ||
    isExporting;
  const isDarkMode = theme === "dark";

  const selectedCampaign = useMemo(
    () => campaigns.find((campaign) => campaign.id === selectedCampaignId) ?? null,
    [campaigns, selectedCampaignId],
  );

  useEffect(() => {
    void loadCampaigns();
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  async function loadCampaigns(selectedId?: string) {
    try {
      setErrorMessage(null);
      setStatusMessage("Refreshing campaign workspace");
      const nextCampaigns = await fetchCampaigns();
      startTransition(() => {
        setCampaigns(nextCampaigns);
        const resolvedSelection =
          selectedId ?? selectedCampaignId ?? nextCampaigns[0]?.id ?? null;
        setSelectedCampaignId(resolvedSelection);
        const selected = nextCampaigns.find((campaign) => campaign.id === resolvedSelection) ?? null;
        setApprovalNotes(selected?.approval_notes ?? "");
      });
      setStatusMessage(nextCampaigns.length ? "Campaign workspace is current" : "No campaigns yet");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load campaigns.";
      setErrorMessage(message);
      setStatusMessage("Campaign workspace is offline");
    }
  }

  async function handleCreateCampaign() {
    if (isCreating) return;
    const validation = validateBrief(formState);
    if (Object.keys(validation).length > 0) {
      setBriefErrors(validation);
      setErrorMessage(null);
      setStatusMessage("Fix the highlighted fields and try again");
      return;
    }
    setBriefErrors({});
    setIsCreating(true);
    try {
      setErrorMessage(null);
      setStatusMessage("Generating campaign bundle");
      const created = await createCampaign(formState);
      await loadCampaigns(created.id);
      setStatusMessage("Campaign generated");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to create campaign.";
      setErrorMessage(humanizeBriefError(message));
      setStatusMessage("Generation failed");
    } finally {
      setIsCreating(false);
    }
  }

  function clearFailureStatus() {
    setStatusMessage((current) =>
      FAILURE_STATUS_RE.test(current) || current === "Fix the highlighted fields and try again"
        ? IDLE_STATUS
        : current,
    );
    setErrorMessage((current) => (current ? null : current));
  }

  function clearBriefError(field: keyof CampaignBrief) {
    setBriefErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  }

  async function handleSelectCampaign(campaignId: string) {
    clearFailureStatus();
    try {
      setErrorMessage(null);
      const campaign = await fetchCampaign(campaignId);
      startTransition(() => {
        setCampaigns((current) =>
          current.map((item) => (item.id === campaign.id ? campaign : item)),
        );
        setSelectedCampaignId(campaign.id);
        setApprovalNotes(campaign.approval_notes ?? "");
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load campaign.";
      setErrorMessage(message);
    }
  }

  async function handleSaveNotes() {
    if (!selectedCampaign || isSaving) return;
    setIsSaving(true);
    try {
      setErrorMessage(null);
      setStatusMessage("Updating campaign notes");
      const updated = await updateCampaign(selectedCampaign.id, {
        approval_notes: approvalNotes,
        metadata: { ...(selectedCampaign.metadata ?? {}), last_editor: "dashboard" },
      });
      replaceCampaign(updated);
      setStatusMessage("Campaign notes updated");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to update campaign.";
      setErrorMessage(message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleApproveCampaign() {
    if (!selectedCampaign || isApproving) return;
    setIsApproving(true);
    try {
      setErrorMessage(null);
      setStatusMessage("Approving campaign");
      const approved = await approveCampaign(selectedCampaign.id, approvalNotes);
      replaceCampaign(approved);
      setStatusMessage("Campaign approved");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to approve campaign.";
      setErrorMessage(message);
    } finally {
      setIsApproving(false);
    }
  }

  async function handleSaveVariant(
    variantIndex: number,
    payload: Pick<AdVariant, "headline" | "primary_text" | "cta" | "image_prompt">,
  ) {
    if (!selectedCampaign || savingVariantIndex !== null) return;
    setSavingVariantIndex(variantIndex);
    try {
      setErrorMessage(null);
      setStatusMessage("Updating campaign variant");
      const updated = await updateCampaignVariant(selectedCampaign.id, variantIndex, payload);
      replaceCampaign(updated);
      setStatusMessage("Campaign variant updated");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to update variant.";
      setErrorMessage(message);
      setStatusMessage("Variant update failed");
    } finally {
      setSavingVariantIndex(null);
    }
  }

  async function handleGenerateVariantImage(variantIndex: number) {
    if (!selectedCampaign || generatingImageIndex !== null) return;
    setGeneratingImageIndex(variantIndex);
    try {
      setErrorMessage(null);
      setStatusMessage("Generating variant image");
      const updated = await generateVariantImage(selectedCampaign.id, variantIndex);
      replaceCampaign(updated);
      const imageStatus = updated.bundle.variants[variantIndex]?.image_status;
      setStatusMessage(imageStatus === "failed" ? "Image generation failed" : "Variant image generated");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to generate image.";
      setErrorMessage(message);
      setStatusMessage("Image generation failed");
    } finally {
      setGeneratingImageIndex(null);
    }
  }

  async function handleExportCampaign() {
    if (!selectedCampaign || isExporting) return;
    setIsExporting(true);
    try {
      setErrorMessage(null);
      setStatusMessage("Preparing export");
      const text = await exportCampaignText(selectedCampaign.id);
      const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${selectedCampaign.bundle.brief.brand_name.replace(/\W+/g, "-").toLowerCase()}-campaign.txt`;
      link.click();
      window.URL.revokeObjectURL(url);
      setStatusMessage("Campaign exported");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to export campaign.";
      setErrorMessage(message);
      setStatusMessage("Export failed");
    } finally {
      setIsExporting(false);
    }
  }

  function replaceCampaign(nextCampaign: CampaignRecord) {
    startTransition(() => {
      setCampaigns((current) => {
        const exists = current.some((item) => item.id === nextCampaign.id);
        return exists
          ? current.map((item) => (item.id === nextCampaign.id ? nextCampaign : item))
          : [nextCampaign, ...current];
      });
      setSelectedCampaignId(nextCampaign.id);
      setApprovalNotes(nextCampaign.approval_notes ?? "");
    });
  }

  function handleFieldChange(field: keyof CampaignBrief, value: string) {
    clearFailureStatus();
    clearBriefError(field);
    setFormState((current) => ({ ...current, [field]: value }));
  }

  function handleListFieldChange(
    field: "pain_points" | "value_props" | "constraints",
    value: string,
  ) {
    clearFailureStatus();
    clearBriefError(field);
    const items = value.split("\n").map((item) => item.trim()).filter(Boolean);
    setFormState((current) => ({ ...current, [field]: items }));
  }

  function handleChannelToggle(channel: string) {
    clearFailureStatus();
    clearBriefError("channels");
    setFormState((current) => {
      const exists = current.channels.includes(channel);
      return {
        ...current,
        channels: exists
          ? current.channels.filter((item) => item !== channel)
          : [...current.channels, channel],
      };
    });
  }

  function toggleTheme() {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }

  function handleReuseBrief() {
    if (!selectedCampaign) return;
    const sourceBrief = selectedCampaign.bundle.brief;
    setBriefErrors({});
    setFormState({
      brand_name: sourceBrief.brand_name,
      product_name: sourceBrief.product_name,
      objective: sourceBrief.objective,
      target_audience: sourceBrief.target_audience,
      pain_points: [...sourceBrief.pain_points],
      value_props: [...sourceBrief.value_props],
      offer: sourceBrief.offer ?? "",
      tone: sourceBrief.tone ?? "",
      channels: [...sourceBrief.channels],
      constraints: [...sourceBrief.constraints],
    });
    setStatusMessage(`Loaded brief from ${sourceBrief.brand_name} into the form`);
  }

  function handleLoadSample() {
    if (isBriefDirty(formState)) {
      const proceed = window.confirm(
        "Load the Northstar AI sample? This will replace your current brief.",
      );
      if (!proceed) return;
    }
    setBriefErrors({});
    clearFailureStatus();
    setFormState(SAMPLE_FORM);
  }

  function handleResetForm() {
    setBriefErrors({});
    clearFailureStatus();
    setFormState(EMPTY_FORM);
  }

  return (
    <div className="app-shell">
      <BriefForm
        formState={formState}
        isPending={isCreating}
        briefErrors={briefErrors}
        onFieldChange={handleFieldChange}
        onListFieldChange={handleListFieldChange}
        onChannelToggle={handleChannelToggle}
        onSubmit={handleCreateCampaign}
        onLoadSample={handleLoadSample}
        onReset={handleResetForm}
      />

      <main className="workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">02 / Pipeline</p>
            <h2>Today&rsquo;s desk</h2>
          </div>
          <div className="header-actions">
            <div className="status-chip" role="status" aria-live="polite">
              {isWorking ? (
                <LoaderCircle className="spin" size={12} aria-hidden="true" />
              ) : (
                <RefreshCw size={12} aria-hidden="true" />
              )}
              <span>{statusMessage}</span>
            </div>
            <button
              className="ghost-action theme-toggle"
              type="button"
              onClick={toggleTheme}
              aria-pressed={isDarkMode}
              aria-label={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDarkMode ? (
                <Sun size={14} aria-hidden="true" />
              ) : (
                <Moon size={14} aria-hidden="true" />
              )}
              {isDarkMode ? "Light mode" : "Dark mode"}
            </button>
            <button className="ghost-action" type="button" onClick={() => void loadCampaigns()}>
              Refresh
            </button>
          </div>
        </header>

        {errorMessage ? (
          <p className="error-banner" role="alert">
            {errorMessage}
          </p>
        ) : null}

        <section className="workspace-grid">
          <CampaignList
            campaigns={campaigns}
            selectedCampaignId={selectedCampaignId}
            onSelect={(id) => void handleSelectCampaign(id)}
          />
          <CampaignDetail
            campaign={selectedCampaign}
            approvalNotes={approvalNotes}
            isSaving={isSaving}
            savingVariantIndex={savingVariantIndex}
            generatingImageIndex={generatingImageIndex}
            isApproving={isApproving}
            isExporting={isExporting}
            onApprovalNotesChange={setApprovalNotes}
            onSaveNotes={handleSaveNotes}
            onSaveVariant={handleSaveVariant}
            onGenerateVariantImage={handleGenerateVariantImage}
            onApprove={handleApproveCampaign}
            onExport={handleExportCampaign}
            onReuseBrief={handleReuseBrief}
          />
        </section>
      </main>
    </div>
  );
}

export default App;
