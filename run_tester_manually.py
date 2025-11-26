"""Manual execution script for the TesterAgent.

This script runs the TesterAgent on the Google Sheets connector to:
1. Generate test cases with mocks
2. Execute tests
3. Report results to test_results.json

Usage:
    source venv/bin/activate
    python run_tester_manually.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

# Add the app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.tester import TesterAgent


async def main():
    """Run the tester agent manually on the Google Sheets connector."""

    # Configuration
    connector_dir = "/Users/amaannawab/research/connector-platform/connector-generator/output/connector-implementations/source-google-sheets"
    connector_name = "google-sheets"
    connector_type = "source"

    logger.info("=" * 70)
    logger.info("MANUAL TESTER AGENT EXECUTION")
    logger.info("=" * 70)
    logger.info(f"Connector: {connector_name}")
    logger.info(f"Directory: {connector_dir}")
    logger.info("=" * 70)

    # Verify connector exists
    connector_path = Path(connector_dir)
    if not connector_path.exists():
        logger.error(f"Connector directory not found: {connector_dir}")
        return

    # List source files
    src_dir = connector_path / "src"
    if src_dir.exists():
        logger.info("\nSource files found:")
        for f in src_dir.glob("*.py"):
            logger.info(f"  - {f.name}")

    # Check for IMPLEMENTATION.md
    impl_md = connector_path / "IMPLEMENTATION.md"
    if impl_md.exists():
        logger.info(f"\nIMPLEMENTATION.md found: {impl_md}")
    else:
        logger.warning("\nIMPLEMENTATION.md NOT found - agent will rely on source code")

    logger.info("\n" + "=" * 70)
    logger.info("Starting TesterAgent execution...")
    logger.info("This will:")
    logger.info("  1. Research Google Sheets API testing patterns (WebSearch)")
    logger.info("  2. Read connector source code")
    logger.info("  3. Create test suite with mocks")
    logger.info("  4. Run pytest")
    logger.info("  5. Write results to tests/test_results.json")
    logger.info("=" * 70 + "\n")

    # Create and run the tester agent
    tester = TesterAgent()

    try:
        result = await tester.execute(
            connector_dir=connector_dir,
            connector_name=connector_name,
            connector_type=connector_type,
        )

        logger.info("\n" + "=" * 70)
        logger.info("TESTER AGENT COMPLETED")
        logger.info("=" * 70)
        logger.info(f"Success: {result.success}")
        logger.info(f"Duration: {result.duration_seconds:.1f}s")
        logger.info(f"Tokens used: {result.tokens_used}")

        if result.error:
            logger.error(f"Error: {result.error}")

        # Parse and display output
        if result.output:
            try:
                output_data = json.loads(result.output)
                logger.info(f"\nTest Status: {output_data.get('status')}")
                logger.info(f"Tests Passed: {output_data.get('unit_tests_passed', 0)}")
                logger.info(f"Tests Failed: {output_data.get('unit_tests_failed', 0)}")

                errors = output_data.get('errors', [])
                if errors:
                    logger.info(f"\nErrors ({len(errors)}):")
                    for i, err in enumerate(errors[:10], 1):
                        logger.info(f"  {i}. {err[:200]}")
            except json.JSONDecodeError:
                logger.info(f"\nRaw output:\n{result.output[:2000]}")

        # Check for test_results.json
        results_file = connector_path / "tests" / "test_results.json"
        if results_file.exists():
            logger.info(f"\n✓ Results file created: {results_file}")
            with open(results_file) as f:
                results = json.load(f)
            logger.info(f"  Status: {results.get('status')}")
            logger.info(f"  Passed: {results.get('passed')}")
            recs = results.get('recommendations', [])
            if recs:
                logger.info(f"  Recommendations:")
                for r in recs[:5]:
                    logger.info(f"    - {r}")
        else:
            logger.warning(f"\n✗ Results file NOT created: {results_file}")

        logger.info("\n" + "=" * 70)

        return result

    except Exception as e:
        logger.exception(f"TesterAgent failed with exception: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
