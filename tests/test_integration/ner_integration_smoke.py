"""Simple integration smoke test for NER LOC detection.

Usage:
    poetry run python tests/test_integration/ner_integration_smoke.py \
      "Recomiéndame planes en Madrid y Barcelona"

Optional:
    poetry run python tests/test_integration/ner_integration_smoke.py \
      "Trip between London and Paris" --language en
"""

import argparse
import asyncio
import sys
from pathlib import Path

import structlog

# Ensure project root is importable when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from integration.external_apis.ner_factory import NERServiceFactory

logger = structlog.get_logger(__name__)


async def run_smoke_test(text: str, language: str | None = None) -> int:
    """Run a quick NER integration check and log detected locations."""
    service = NERServiceFactory.create_from_env()
    service_info = service.get_service_info()

    logger.info(
        "ner_smoke_test_started",
        provider=service_info.get("provider"),
        language=language,
        available=service_info.get("available"),
    )

    result = await service.extract_locations(text=text, language=language)
    locations = result.get("locations", [])

    logger.info(
        "ner_loc_detected",
        input_text=text,
        provider=result.get("provider"),
        model=result.get("model"),
        language=result.get("language"),
        top_location=result.get("top_location"),
        locations=locations,
        total_locations=len(locations),
        status=result.get("status"),
    )

    if not locations:
        logger.warning("ner_smoke_test_no_locations_found")
        return 1

    logger.info("ner_smoke_test_success")
    return 0


def main() -> int:
    """CLI entrypoint for quick integration validation."""
    parser = argparse.ArgumentParser(description="NER integration smoke test (LOC detection)")
    parser.add_argument("text", help="Input text to analyze")
    parser.add_argument("--language", default=None, help="Language code override, e.g. es/en")
    args = parser.parse_args()

    return asyncio.run(run_smoke_test(text=args.text, language=args.language))


if __name__ == "__main__":
    raise SystemExit(main())
