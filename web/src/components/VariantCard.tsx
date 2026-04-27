import type { AdVariant } from "../types";
import { apiBaseUrl, formatChannel } from "../utils";

type VariantCardProps = {
  variant: AdVariant;
};

function VariantCard({ variant }: VariantCardProps) {
  return (
    <article className="variant-item">
      <div className="variant-head">
        <span className="channel-chip">{formatChannel(variant.channel)}</span>
        <span>{variant.cta}</span>
      </div>
      <h5>{variant.headline}</h5>
      {variant.generated_asset ? (
        <img
          className="variant-image"
          src={`${apiBaseUrl()}${variant.generated_asset.path}`}
          alt={variant.headline}
        />
      ) : null}
      <p>{variant.primary_text}</p>
      <div className="prompt-block">
        <span>Image prompt</span>
        <p>{variant.image_prompt}</p>
      </div>
    </article>
  );
}

export default VariantCard;
