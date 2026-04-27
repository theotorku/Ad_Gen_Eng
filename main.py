from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ad_engine import AdGenerationEngine, run_api_server  # noqa: E402


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


SAMPLE_BRIEF = {
    "brand_name": "Northstar AI",
    "product_name": "CampaignPilot",
    "objective": "Generate more qualified demo requests",
    "target_audience": "B2B marketing teams at growth-stage SaaS companies",
    "pain_points": [
        "slow campaign production cycles",
        "generic creative that underperforms",
    ],
    "value_props": [
        "faster ad iteration",
        "clearer campaign strategy",
        "less manual copy drafting",
    ],
    "offer": "Book a free strategy walkthrough",
    "tone": "confident",
    "channels": ["linkedin", "facebook", "google_search"],
    "constraints": ["Avoid exaggerated performance claims"],
}


def load_dotenv(dotenv_path: Path | None = None) -> None:
    path = dotenv_path or (ROOT / ".env")
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_brief_from_args() -> dict:
    if len(sys.argv) < 2:
        return SAMPLE_BRIEF

    input_path = Path(sys.argv[1]).resolve()
    with input_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    load_dotenv()

    if len(sys.argv) >= 2 and sys.argv[1] == "serve":
        host = sys.argv[2] if len(sys.argv) >= 3 else DEFAULT_HOST
        port = int(sys.argv[3]) if len(sys.argv) >= 4 else DEFAULT_PORT
        run_api_server(host=host, port=port)
        return

    brief = load_brief_from_args()
    engine = AdGenerationEngine()
    bundle = engine.run(brief)
    print(json.dumps(bundle.to_dict(), indent=2))


if __name__ == "__main__":
    main()
