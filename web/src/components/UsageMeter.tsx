import { Gauge } from "lucide-react";
import type { UsageSummary } from "../types";

type UsageMeterProps = {
  usage: UsageSummary | null;
  onUpgrade?: () => void;
};

function formatLimit(limit: number | null): string {
  return limit === null ? "∞" : String(limit);
}

function isAtLimit(used: number, limit: number | null): boolean {
  return limit !== null && used >= limit;
}

function UsageMeter({ usage, onUpgrade }: UsageMeterProps) {
  if (!usage) return null;

  const planLabel = usage.plan.charAt(0).toUpperCase() + usage.plan.slice(1);
  const campaignsCapped = isAtLimit(usage.usage.campaigns, usage.limits.campaigns);
  const imagesCapped = isAtLimit(usage.usage.images, usage.limits.images);
  const nearLimit = usage.enforced && (campaignsCapped || imagesCapped);

  return (
    <div className="usage-meter" role="group" aria-label="Plan usage this month">
      <Gauge size={12} aria-hidden="true" />
      <span className="usage-plan">{planLabel}</span>
      <span className={campaignsCapped ? "usage-stat capped" : "usage-stat"}>
        {usage.usage.campaigns}/{formatLimit(usage.limits.campaigns)} campaigns
      </span>
      <span className={imagesCapped ? "usage-stat capped" : "usage-stat"}>
        {usage.usage.images}/{formatLimit(usage.limits.images)} images
      </span>
      {onUpgrade && (usage.plan === "free" || nearLimit) ? (
        <button className="usage-upgrade" type="button" onClick={onUpgrade}>
          Upgrade
        </button>
      ) : null}
    </div>
  );
}

export default UsageMeter;
