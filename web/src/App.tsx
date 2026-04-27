import { useEffect, useMemo, useState, useTransition } from "react";
import { LoaderCircle, RefreshCw } from "lucide-react";
import {
  approveCampaign,
  createCampaign,
  fetchCampaign,
  fetchCampaigns,
  updateCampaign,
} from "./api";
import type { CampaignBrief, CampaignRecord } from "./types";
import { SAMPLE_FORM } from "./constants";
import BriefForm from "./components/BriefForm";
import CampaignList from "./components/CampaignList";
import CampaignDetail from "./components/CampaignDetail";

function App() {
  const [campaigns, setCampaigns] = useState<CampaignRecord[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [formState, setFormState] = useState<CampaignBrief>(SAMPLE_FORM);
  const [approvalNotes, setApprovalNotes] = useState("");
  const [statusMessage, setStatusMessage] = useState("Loading campaigns");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const selectedCampaign = useMemo(
    () => campaigns.find((campaign) => campaign.id === selectedCampaignId) ?? null,
    [campaigns, selectedCampaignId],
  );

  useEffect(() => {
    void loadCampaigns();
  }, []);

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
    try {
      setErrorMessage(null);
      setStatusMessage("Generating campaign bundle");
      const created = await createCampaign(formState);
      await loadCampaigns(created.id);
      setStatusMessage("Campaign generated");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to create campaign.";
      setErrorMessage(message);
      setStatusMessage("Generation failed");
    }
  }

  async function handleSelectCampaign(campaignId: string) {
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
    if (!selectedCampaign) return;
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
    }
  }

  async function handleApproveCampaign() {
    if (!selectedCampaign) return;
    try {
      setErrorMessage(null);
      setStatusMessage("Approving campaign");
      const approved = await approveCampaign(selectedCampaign.id, approvalNotes);
      replaceCampaign(approved);
      setStatusMessage("Campaign approved");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to approve campaign.";
      setErrorMessage(message);
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
    setFormState((current) => ({ ...current, [field]: value }));
  }

  function handleListFieldChange(
    field: "pain_points" | "value_props" | "constraints",
    value: string,
  ) {
    const items = value.split("\n").map((item) => item.trim()).filter(Boolean);
    setFormState((current) => ({ ...current, [field]: items }));
  }

  function handleChannelToggle(channel: string) {
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

  return (
    <div className="app-shell">
      <BriefForm
        formState={formState}
        isPending={isPending}
        onFieldChange={handleFieldChange}
        onListFieldChange={handleListFieldChange}
        onChannelToggle={handleChannelToggle}
        onSubmit={handleCreateCampaign}
      />

      <main className="workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">02 / Pipeline</p>
            <h2>Today&rsquo;s desk</h2>
          </div>
          <div className="header-actions">
            <div className="status-chip">
              {isPending ? <LoaderCircle className="spin" size={12} /> : <RefreshCw size={12} />}
              <span>{statusMessage}</span>
            </div>
            <button className="ghost-action" type="button" onClick={() => void loadCampaigns()}>
              Refresh
            </button>
          </div>
        </header>

        {errorMessage ? <p className="error-banner">{errorMessage}</p> : null}

        <section className="workspace-grid">
          <CampaignList
            campaigns={campaigns}
            selectedCampaignId={selectedCampaignId}
            onSelect={(id) => void handleSelectCampaign(id)}
          />
          <CampaignDetail
            campaign={selectedCampaign}
            approvalNotes={approvalNotes}
            onApprovalNotesChange={setApprovalNotes}
            onSaveNotes={handleSaveNotes}
            onApprove={handleApproveCampaign}
          />
        </section>
      </main>
    </div>
  );
}

export default App;
