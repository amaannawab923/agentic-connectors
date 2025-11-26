"""Manual execution script for the TesterAgent in RERUN mode.

This script runs the TesterAgent in RERUN mode on the Google Sheets connector
to verify that the RERUN mode works correctly (just runs existing tests
without regenerating them).

Usage:
    source venv/bin/activate
    python run_tester_rerun_manually.py
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

from app.agents.tester import TesterAgent, TesterMode


async def main():
    """Run the tester agent manually in RERUN mode on the Google Sheets connector."""

    # Configuration
    connector_dir = "/Users/amaannawab/research/connector-platform/connector-generator/output/connector-implementations/source-google-sheets"
    connector_name = "google-sheets"
    connector_type = "source"

    logger.info("=" * 70)
    logger.info("MANUAL TESTER AGENT EXECUTION - RERUN MODE")
    logger.info("=" * 70)
    logger.info(f"Connector: {connector_name}")
    logger.info(f"Directory: {connector_dir}")
    logger.info(f"Mode: RERUN (just run existing tests)")
    logger.info("=" * 70)

    # Verify connector exists
    connector_path = Path(connector_dir)
    if not connector_path.exists():
        logger.error(f"Connector directory not found: {connector_dir}")
        return

    # Check for existing tests
    tests_dir = connector_path / "tests"
    if not tests_dir.exists():
        logger.error(f"Tests directory not found: {tests_dir}")
        logger.error("RERUN mode requires existing tests. Run in GENERATE mode first.")
        return

    test_files = list(tests_dir.glob("test_*.py"))
    logger.info(f"\nExisting test files ({len(test_files)}):")
    for f in test_files:
        logger.info(f"  - {f.name}")

    # Check for conftest.py
    conftest = tests_dir / "conftest.py"
    if conftest.exists():
        logger.info(f"  - conftest.py (fixtures)")
    else:
        logger.warning("  - conftest.py NOT found")

    logger.info("\n" + "=" * 70)
    logger.info("Starting TesterAgent in RERUN mode...")
    logger.info("This will:")
    logger.info("  1. Setup environment (venv)")
    logger.info("  2. Generate RSA key if needed")
    logger.info("  3. Run existing tests (pytest)")
    logger.info("  4. Write results to tests/test_results.json")
    logger.info("")
    logger.info("It will NOT:")
    logger.info("  - Research testing patterns")
    logger.info("  - Modify any test files")
    logger.info("  - Create new tests")
    logger.info("=" * 70 + "\n")

    # Create and run the tester agent in RERUN mode
    tester = TesterAgent()

    try:
        result = await tester.execute(
            connector_dir=connector_dir,
            connector_name=connector_name,
            connector_type=connector_type,
            mode=TesterMode.RERUN,  # Use RERUN mode
        )

        logger.info("\n" + "=" * 70)
        logger.info("TESTER AGENT (RERUN MODE) COMPLETED")
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
            logger.info(f"\n Results file: {results_file}")
            with open(results_file) as f:
                results = json.load(f)
            logger.info(f"  Status: {results.get('status')}")
            logger.info(f"  Passed: {results.get('passed')}")
            logger.info(f"  Tests run: {results.get('tests_run', 0)}")
            logger.info(f"  Tests passed: {results.get('tests_passed', 0)}")
            logger.info(f"  Tests failed: {results.get('tests_failed', 0)}")
        else:
            logger.warning(f"\n Results file NOT created: {results_file}")

        logger.info("\n" + "=" * 70)

        return result

    except Exception as e:
        logger.exception(f"TesterAgent failed with exception: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
