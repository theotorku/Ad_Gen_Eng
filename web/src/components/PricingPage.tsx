import { PricingTable } from "@clerk/clerk-react";

type PricingPageProps = {
  onBack: () => void;
};

function PricingPage({ onBack }: PricingPageProps) {
  return (
    <main className="pricing-screen">
      <header className="pricing-header">
        <div>
          <p className="eyebrow">Plans</p>
          <h1>Choose your workspace plan</h1>
          <p className="pricing-subhead">
            Flat monthly pricing — no credits, no surprise bills. Plans apply to your
            whole workspace and every seat on it.
          </p>
        </div>
        <button className="ghost-action" type="button" onClick={onBack}>
          Back to studio
        </button>
      </header>
      <section className="pricing-table-wrap">
        <PricingTable for="organization" />
      </section>
    </main>
  );
}

export default PricingPage;
