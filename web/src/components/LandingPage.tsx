import { useEffect, useState } from "react";
import { 
  Terminal, 
  Settings, 
  Shield, 
  Zap, 
  Layers, 
  ArrowRight, 
  Eye, 
  CheckCircle2, 
  Cpu, 
  Sparkles,
  Sun,
  Moon,
  Github
} from "lucide-react";

type PresetBrief = {
  id: string;
  brand_name: string;
  product_name: string;
  objective: string;
  target_audience: string;
  tone: string;
  strategy: {
    positioning: string;
    pain_points: string[];
    value_props: string[];
  };
  variants: {
    channel: string;
    headline: string;
    primary_text: string;
    cta: string;
    image_prompt: string;
  }[];
};

const PRESETS: Record<string, PresetBrief> = {
  ecoskin: {
    id: "ecoskin",
    brand_name: "EcoSkin",
    product_name: "Zero-Waste botanical cream",
    objective: "Introduce zero-waste, organic skincare line.",
    target_audience: "Eco-conscious millennials & Gen-Z",
    tone: "Warm, authentic, clean, botanical",
    strategy: {
      positioning: "Pure botanical nourishment that leaves no trace on Earth.",
      pain_points: [
        "Unrecyclable plastic packaging polluting oceans",
        "Synthetic chemical irritation on sensitive skin",
        "Greenwashing from mainstream beauty labels"
      ],
      value_props: [
        "100% compostable bamboo and glass container",
        "USDA certified organic botanical extracts",
        "Dermatologist tested, toxin-free performance"
      ]
    },
    variants: [
      {
        channel: "instagram",
        headline: "Skincare that honors your skin—and the Earth.",
        primary_text: "Discover the world's first zero-waste botanical face cream. Certified organic, fully biodegradable packaging, and pure clinical nourishment.",
        cta: "Shop EcoSkin",
        image_prompt: "A beautiful minimalist frosted compostable jar sitting on a damp stone in a sunlit forest, organic leaves and moss, water droplets, soft cinematic macro photography."
      },
      {
        channel: "facebook",
        headline: "100% Organic. 0% Waste.",
        primary_text: "Most skincare brands leave behind plastic that lasts centuries. EcoSkin nourishes your skin with rich botanicals and comes in a 100% compostable bamboo container. Take care of your body and the planet.",
        cta: "Learn More",
        image_prompt: "Flatlay of organic skincare ingredients—green tea leaves, avocado seed, aloe vera stalks arranged next to a textured compostable jar on raw linen."
      },
      {
        channel: "linkedin",
        headline: "The Future of Luxury Skincare is Circular.",
        primary_text: "We spent 3 years engineering a high-performance face cream that leaves zero trace. Read the story of how EcoSkin is proving that luxury skincare can be 100% zero-waste and circular.",
        cta: "Read Article",
        image_prompt: "Professional workspace with a clean wooden desk, a sleek green notebook, a compostable jar, and soft window lighting, business chic."
      }
    ]
  },
  devpulse: {
    id: "devpulse",
    brand_name: "DevPulse",
    product_name: "DevPulse Analytics",
    objective: "Drive trial sign-ups for engineering metrics tracker.",
    target_audience: "Engineering managers and CTOs at scaleups",
    tone: "Direct, technical, performance-driven",
    strategy: {
      positioning: "Eliminate development bottlenecks with real-time git and deployment telemetry.",
      pain_points: [
        "Misaligned sprint metrics that don't match shipping reality",
        "Developer burnout hidden behind silent task bottlenecks",
        "Unpredictable release dates causing stakeholder friction"
      ],
      value_props: [
        "60-second zero-config setup with GitHub & Jira",
        "Automated sprint velocity forecasting with machine learning",
        "Slack alerts identifying active bottleneck risks before they slip"
      ]
    },
    variants: [
      {
        channel: "linkedin",
        headline: "Stop guessing your engineering velocity.",
        primary_text: "DevPulse connects to your git and deployment pipelines in 60 seconds to highlight actual bottlenecks, predict launch slippage, and proactively guard against developer burnout. No manual standups needed.",
        cta: "Book a Demo",
        image_prompt: "Sleek dark-mode workspace displaying real-time analytics graphs on a wide curved monitor, high-contrast violet and cyan glowing UI elements, clean typography, editorial style."
      },
      {
        channel: "facebook",
        headline: "Engineering managers: See the full picture.",
        primary_text: "Tired of sprint updates that don't match reality? DevPulse gives you automated pipeline analytics, velocity charts, and burnout indicators directly in Slack. Built by developers, for engineering leaders.",
        cta: "Start Free Trial",
        image_prompt: "Minimalist workspace with a coffee cup, keyboard, and a laptop showing developer metrics dashboards, vibrant accent lighting."
      }
    ]
  },
  bloomroasters: {
    id: "bloomroasters",
    brand_name: "BloomRoasters",
    product_name: "Bloom Coffee Club",
    objective: "Grow monthly subscription signups for coffee deliveries.",
    target_audience: "Specialty coffee hobbyists and office connoisseurs",
    tone: "Passionate, sensory, artisanal, educational",
    strategy: {
      positioning: "Freshly roasted single-origin coffees from direct-trade farms directly to your door.",
      pain_points: [
        "Stale, dusty supermarket coffee sitting on shelves for months",
        "Total lack of source farm transparency and fair pay tracking",
        "Repetitive, boring flavor profiles without sensory description"
      ],
      value_props: [
        "Roasted and shipped within 24 hours of roasting",
        "100% direct-trade verified compensation reports per lot",
        "Custom flavor matchmaking profile with sensory guide"
      ]
    },
    variants: [
      {
        channel: "instagram",
        headline: "Roasted today. At your door tomorrow.",
        primary_text: "Experience single-origin coffee at its absolute peak. Freshly roasted micro-lots from ethical, direct-trade farms in Ethiopia and Colombia. Tailored to your brew style, delivered weekly.",
        cta: "Join the Club",
        image_prompt: "Close up of fresh espresso dripping from a portafilter into a modern ceramic cup, beautiful rich crema, warm steam rising, golden hour lighting, cinematic macro."
      },
      {
        channel: "facebook",
        headline: "Tired of stale supermarket beans?",
        primary_text: "Store-bought coffee is often months old before you grind it. Bloom Coffee Club roasts and ships single-origin micro-lots within 24 hours. Every box includes tasting cards and a brewing guide.",
        cta: "Find Your Roast",
        image_prompt: "Warm, rustic kitchen setup. A brown paper coffee bag with a custom stamped label sitting next to coffee beans, a hand grinder, and a fresh pour-over dripper."
      }
    ]
  }
};

const DEFAULT_PRESET = PRESETS.ecoskin as PresetBrief;

type LandingPageProps = {
  onLaunchStudio: () => void;
};

export default function LandingPage({ onLaunchStudio }: LandingPageProps) {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const stored = window.localStorage.getItem("ad_engine_theme");
    if (stored === "light" || stored === "dark") return stored;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  const [activePreset, setActivePreset] = useState<PresetBrief>(DEFAULT_PRESET);
  const [simulationState, setSimulationState] = useState<"idle" | "validating" | "strategy" | "variants">("idle");
  const [simLog, setSimLog] = useState<string[]>([]);
  const [providerTab, setProviderTab] = useState<"copy" | "image" | "database">("copy");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("ad_engine_theme", theme);
  }, [theme]);

  function toggleTheme() {
    setTheme((c) => (c === "dark" ? "light" : "dark"));
  }

  function startSimulation(preset: PresetBrief) {
    setActivePreset(preset);
    setSimulationState("validating");
    setSimLog([]);

    // Step 1: Validation simulation
    const logs1 = [
      "Connecting to brief validator...",
      "Analyzing campaign objective: \"" + preset.objective + "\"",
      "✓ Campaign brief structure: VALID"
    ];
    
    let i = 0;
    const interval = setInterval(() => {
      const nextLog = logs1[i];
      if (nextLog) {
        setSimLog((prev) => [...prev, nextLog]);
        i++;
      } else {
        clearInterval(interval);
        
        // Step 2: Strategy creation
        setTimeout(() => {
          setSimulationState("strategy");
          setSimLog((prev) => [...prev, "Compiling creative strategy matrices...", "✓ Strategy formulation complete."]);
          
          // Step 3: Variants adaptation
          setTimeout(() => {
            setSimulationState("variants");
            setSimLog((prev) => [...prev, "Adapting copy to requested channels...", "✓ Generation finished. Ready for review."]);
          }, 1500);
        }, 1200);
      }
    }, 400);
  }

  return (
    <div className="landing-container">
      {/* Editorial Header */}
      <header className="landing-header">
        <div className="landing-header-inner">
          <div className="landing-brand">
            <h1 className="wordmark">
              AD/GEN<em>ENGINE</em>
            </h1>
            <span className="branding-dot" />
          </div>
          
          <nav className="landing-nav">
            <a href="#simulator" className="nav-link">Simulator</a>
            <a href="#features" className="nav-link">Architecture</a>
            <a href="#providers" className="nav-link">Providers</a>
            <button 
              className="ghost-action theme-toggle" 
              type="button" 
              onClick={toggleTheme}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
              <span>{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
            </button>
            <button className="primary-inline" type="button" onClick={onLaunchStudio}>
              Launch Studio <ArrowRight size={13} />
            </button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="landing-hero">
        <div className="hero-content">
          <p className="eyebrow">01 / GEN-ADVERTISING ENGINE</p>
          <h2 className="hero-title">
            Structured Ad Bundles.<br />
            Powered by <em>Creative Strategy.</em>
          </h2>
          <p className="hero-subtitle">
            An editorial-grade campaign engine that transforms raw briefs into high-converting, channel-specific copy and optimized image assets. Pluggable, transparent, and built for modern creative teams.
          </p>
          <div className="hero-ctas">
            <button className="primary-action hero-cta-btn" type="button" onClick={onLaunchStudio}>
              Launch Creative Studio <ArrowRight size={16} />
            </button>
            <a href="#simulator" className="ghost-action hero-cta-btn-secondary">
              Try Interactive Simulator
            </a>
          </div>
        </div>
      </section>

      {/* Interactive Simulator Section */}
      <section id="simulator" className="landing-section simulator-section">
        <div className="section-marker">
          <span className="num">02</span>
          <h2>The Engine In Action</h2>
        </div>
        
        <div className="simulator-grid">
          {/* Brief Input Column */}
          <div className="sim-panel sim-inputs">
            <h3>Choose a Brand Brief Preset</h3>
            <p className="panel-desc">
              Select one of our pre-configured campaign briefs to watch how the engine validates inputs, drafts positioning strategy, and tailors output variants.
            </p>
            
            <div className="preset-selector">
              {Object.values(PRESETS).map((p) => (
                <button
                  key={p.id}
                  className={`preset-btn ${activePreset.id === p.id ? "active" : ""}`}
                  onClick={() => {
                    setActivePreset(p);
                    setSimulationState("idle");
                    setSimLog([]);
                  }}
                  type="button"
                >
                  <Sparkles size={13} className="sparkle-icon" />
                  <div>
                    <span className="preset-name">{p.brand_name}</span>
                    <span className="preset-tagline">{p.product_name}</span>
                  </div>
                </button>
              ))}
            </div>

            <div className="brief-card-preview">
              <div className="brief-preview-row">
                <span className="preview-label">Objective:</span>
                <span className="preview-val">{activePreset.objective}</span>
              </div>
              <div className="brief-preview-row">
                <span className="preview-label">Target Audience:</span>
                <span className="preview-val">{activePreset.target_audience}</span>
              </div>
              <div className="brief-preview-row">
                <span className="preview-label">Tone:</span>
                <span className="preview-val">{activePreset.tone}</span>
              </div>
            </div>

            <button 
              className="primary-action sim-run-btn" 
              onClick={() => startSimulation(activePreset)}
              disabled={simulationState !== "idle" && simulationState !== "variants"}
              type="button"
            >
              {simulationState === "idle" || simulationState === "variants" ? (
                <>
                  <Cpu size={14} /> Simulate Creative Strategy
                </>
              ) : (
                "Processing Brief..."
              )}
            </button>
          </div>

          {/* Simulated Output Column */}
          <div className="sim-panel sim-outputs">
            <div className="sim-output-header">
              <h3>Simulation Pipeline</h3>
              {simulationState !== "idle" && (
                <span className="sim-badge pulse-badge">{simulationState}</span>
              )}
            </div>

            {simulationState === "idle" ? (
              <div className="sim-empty-state">
                <Terminal size={32} className="terminal-icon" />
                <p>Click <strong>"Simulate Creative Strategy"</strong> to initiate the automated generation pipeline.</p>
              </div>
            ) : (
              <div className="sim-timeline">
                {/* Micro Terminal Log */}
                <div className="sim-terminal-block">
                  <div className="terminal-head">
                    <span className="dot red" />
                    <span className="dot yellow" />
                    <span className="dot green" />
                    <span className="terminal-title">pipeline.log</span>
                  </div>
                  <pre className="terminal-body">
                    {simLog.map((log, idx) => (
                      <div key={idx} className="terminal-line">
                        <span className="term-prompt">$</span> {log}
                      </div>
                    ))}
                    {simulationState !== "variants" && (
                      <div className="terminal-line typing">
                        <span className="term-prompt">$</span> compiling...
                        <span className="cursor" />
                      </div>
                    )}
                  </pre>
                </div>

                {/* Step 2: Strategy Plan Display */}
                {(simulationState === "strategy" || simulationState === "variants") && (
                  <div className="sim-strategy-result fade-in-up">
                    <div className="section-title-small">
                      <CheckCircle2 size={13} className="checked-icon" /> Generated Strategy Matrix
                    </div>
                    
                    <div className="strategy-matrix-card">
                      <div className="matrix-field">
                        <strong>Positioning Statement</strong>
                        <p className="statement">"{activePreset.strategy.positioning}"</p>
                      </div>
                      <div className="matrix-two-col">
                        <div className="matrix-subfield">
                          <strong>Target Pain Points</strong>
                          <ul>
                            {activePreset.strategy.pain_points.map((pt, i) => (
                              <li key={i}>{pt}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="matrix-subfield">
                          <strong>Differentiating Value Props</strong>
                          <ul>
                            {activePreset.strategy.value_props.map((vp, i) => (
                              <li key={i}>{vp}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Step 3: Variants Adaptation Display */}
                {simulationState === "variants" && (
                  <div className="sim-variants-result fade-in-up">
                    <div className="section-title-small">
                      <CheckCircle2 size={13} className="checked-icon" /> Channel-Specific Variants
                    </div>
                    
                    <div className="sim-variants-carousel">
                      {activePreset.variants.map((v, i) => (
                        <div key={i} className="sim-variant-card">
                          <div className="sim-variant-head">
                            <span className="channel-pill">{v.channel}</span>
                            <span className="cta-action">{v.cta}</span>
                          </div>
                          <h4 className="sim-variant-headline">{v.headline}</h4>
                          <p className="sim-variant-copy">{v.primary_text}</p>
                          <div className="sim-prompt-box">
                            <span className="prompt-label">Optimized Image Prompt</span>
                            <p>{v.image_prompt}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Core Architecture Section */}
      <section id="features" className="landing-section features-section">
        <div className="section-marker">
          <span className="num">03</span>
          <h2>Platform Architecture</h2>
        </div>

        <div className="features-grid">
          <div className="feature-item">
            <Layers size={20} className="feature-icon" />
            <h4>Pluggable Provider Architecture</h4>
            <p>Decouple logic from AI platforms. Seamlessly switch planning, copy drafting, and image models via clean backend protocols and configuration tokens.</p>
          </div>
          <div className="feature-item">
            <Zap size={20} className="feature-icon" />
            <h4>Lightweight Strategy Core</h4>
            <p>Unlike generic prompts, the engine forces an initial validation and strategic positioning pass before drafting any channel-specific ad creative.</p>
          </div>
          <div className="feature-item">
            <Shield size={20} className="feature-icon" />
            <h4>Enterprise Grade Scoping</h4>
            <p>Out-of-the-box Clerk authentication, multi-tenant organization scoping, database row segregation, and secure REST API key validations.</p>
          </div>
          <div className="feature-item">
            <Settings size={20} className="feature-icon" />
            <h4>Durable Local Storage</h4>
            <p>Toggle between lightweight process memory, robust local SQLite instances for developers, and production-ready PostgreSQL databases.</p>
          </div>
        </div>
      </section>

      {/* Provider Details & Environment Setup */}
      <section id="providers" className="landing-section providers-section">
        <div className="section-marker">
          <span className="num">04</span>
          <h2>Provider Stack & Deployment</h2>
        </div>

        <div className="providers-layout">
          <div className="providers-info">
            <h3>Designed for Local Dev & Production Scale</h3>
            <p>
              The engine structures campaign building into three core layers. By editing a few environment parameters in your local <code>.env</code> file, you can immediately shift from zero-cost offline rules to paid OpenAI production stacks.
            </p>
            
            <div className="tab-triggers">
              <button 
                className={`tab-trigger ${providerTab === "copy" ? "active" : ""}`}
                onClick={() => setProviderTab("copy")}
                type="button"
              >
                Copy & Copywriters
              </button>
              <button 
                className={`tab-trigger ${providerTab === "image" ? "active" : ""}`}
                onClick={() => setProviderTab("image")}
                type="button"
              >
                Image Assets
              </button>
              <button 
                className={`tab-trigger ${providerTab === "database" ? "active" : ""}`}
                onClick={() => setProviderTab("database")}
                type="button"
              >
                Durable Storage
              </button>
            </div>
            
            <div className="tab-explanation">
              {providerTab === "copy" && (
                <p>
                  <strong>Planning & Copy Providers:</strong> Use <code>rule_based</code> matching during offline development to output highly structured templates, or plug in a live custom LLM provider interface by implementing the protocols in <code>src/ad_engine/providers.py</code>.
                </p>
              )}
              {providerTab === "image" && (
                <p>
                  <strong>Image & Prompt Generation:</strong> Generate rich descriptive prompts with zero credits using <code>prompt_template</code>. Switch <code>openai_images</code> on when ready to query DALL-E, customize sizes, format outputs, and auto-download results to your asset folder.
                </p>
              )}
              {providerTab === "database" && (
                <p>
                  <strong>Durable Store:</strong> Use <code>memory</code> for testing. Transition to <code>sqlite</code> for persistent desktop work with local DB files, or drop in standard PostgreSQL DSN credentials for shared team deployments.
                </p>
              )}
            </div>
          </div>

          <div className="providers-code">
            <div className="code-block-header">
              <span>Environment Configuration</span>
              <span className="lang-tag">.env</span>
            </div>
            <pre className="code-content">
              {providerTab === "copy" && (
`# Pluggable planning & drafting
AD_ENGINE_PLANNING_PROVIDER=rule_based
AD_ENGINE_COPY_PROVIDER=rule_based

# Enable custom LLM providers when needed
# AD_ENGINE_COPY_PROVIDER=openai`
              )}
              {providerTab === "image" && (
`# Image generation provider
AD_ENGINE_IMAGE_PROVIDER=openai_images
OPENAI_API_KEY=sk-proj-prod_example...

# Advanced generator controls
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_SIZE=1024x1024
OPENAI_IMAGE_OUTPUT_DIR=./data/generated_assets`
              )}
              {providerTab === "database" && (
`# Configure DB persistence backend
AD_ENGINE_DB_BACKEND=sqlite
AD_ENGINE_SQLITE_PATH=./data/ad_engine.db

# Production database deployment
# AD_ENGINE_DB_BACKEND=postgres
# AD_ENGINE_POSTGRES_DSN=postgresql://user:pass@host:5432/db`
              )}
            </pre>
          </div>
        </div>
      </section>

      {/* Branded Editorial Footer */}
      <footer className="landing-footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <h3 className="wordmark">
              AD/GEN<em>ENGINE</em>
            </h3>
            <p>Precision advertising automation. Built with bone & ink aesthetics.</p>
          </div>
          
          <div className="footer-links">
            <div className="footer-col">
              <h5>Project</h5>
              <a href="#simulator">Simulator</a>
              <a href="#features">Architecture</a>
              <a href="#providers">Providers</a>
            </div>
            <div className="footer-col">
              <h5>Workspace</h5>
              <button onClick={onLaunchStudio} className="footer-link-btn" type="button">Creative Studio</button>
              <a href="/docs/api.md" className="footer-link">API Specification</a>
            </div>
            <div className="footer-col">
              <h5>Community</h5>
              <a href="https://github.com" target="_blank" rel="noreferrer" className="footer-social-link">
                <Github size={12} /> GitHub
              </a>
            </div>
          </div>
        </div>
        <div className="footer-copyright">
          <span>&copy; {new Date().getFullYear()} Ad Generation Engine. All rights reserved.</span>
          <span>Version 1.2 — Bucket E Edition</span>
        </div>
      </footer>
    </div>
  );
}
