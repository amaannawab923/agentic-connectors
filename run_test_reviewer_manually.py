"""Manual execution script for the TestReviewerAgent.

This script runs the TestReviewerAgent on the Google Sheets connector
test results to determine whether to route to Generator or Tester.

Usage:
    source venv/bin/activate
    python run_test_reviewer_manually.py
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

from app.agents.test_reviewer import TestReviewerAgent


async def main():
    """Run the test reviewer agent manually on the Google Sheets connector."""

    # Configuration
    connector_dir = "/Users/amaannawab/research/connector-platform/connector-generator/output/connector-implementations/source-google-sheets"
    connector_name = "google-sheets"

    logger.info("=" * 70)
    logger.info("MANUAL TEST REVIEWER AGENT EXECUTION")
    logger.info("=" * 70)
    logger.info(f"Connector: {connector_name}")
    logger.info(f"Directory: {connector_dir}")
    logger.info("=" * 70)

    # Load test results from file
    results_file = Path(connector_dir) / "tests" / "test_results.json"
    if not results_file.exists():
        logger.error(f"Test results file not found: {results_file}")
        logger.error("Run the TesterAgent first to generate test results.")
        return

    with open(results_file) as f:
        test_output = json.load(f)

    logger.info("\nTest Results Summary (from tester):")
    logger.info(f"  Status: {test_output.get('status')}")
    logger.info(f"  Passed: {test_output.get('passed')}")
    logger.info(f"  Tests Run: {test_output.get('tests_run')}")
    logger.info(f"  Tests Passed: {test_output.get('tests_passed')}")
    logger.info(f"  Tests Failed: {test_output.get('tests_failed')}")

    import_errors = test_output.get('import_errors', [])
    if import_errors:
        logger.info(f"\n  Import Errors ({len(import_errors)}):")
        for err in import_errors[:3]:
            logger.info(f"    - {err[:100]}...")

    recommendations = test_output.get('recommendations', [])
    if recommendations:
        logger.info(f"\n  Recommendations ({len(recommendations)}):")
        for rec in recommendations[:3]:
            logger.info(f"    - {rec[:100]}...")

    logger.info("\n" + "=" * 70)
    logger.info("Starting TestReviewerAgent execution...")
    logger.info("This will analyze the test results and decide:")
    logger.info("  - INVALID: Tests are wrong -> route to Tester")
    logger.info("  - VALID_FAIL: Code has bugs -> route to Generator")
    logger.info("  - VALID_PASS: All good -> route to Reviewer")
    logger.info("=" * 70 + "\n")

    # Create and run the test reviewer agent
    reviewer = TestReviewerAgent()

    try:
        result = await reviewer.execute(
            connector_dir=connector_dir,
            connector_name=connector_name,
            test_output=test_output,
        )

        logger.info("\n" + "=" * 70)
        logger.info("TEST REVIEWER AGENT COMPLETED")
        logger.info("=" * 70)

        # Display the verdict
        decision = result.get('decision', 'UNKNOWN')
        confidence = result.get('confidence', 0.0)
        analysis = result.get('analysis', '')
        root_cause = result.get('root_cause_location', 'unknown')

        logger.info(f"\n{'*' * 50}")
        logger.info(f"  VERDICT: {decision}")
        logger.info(f"  CONFIDENCE: {confidence:.0%}")
        logger.info(f"  ROOT CAUSE LOCATION: {root_cause}")
        logger.info(f"{'*' * 50}")

        # Route decision
        if decision == "VALID_FAIL":
            logger.info(f"\n  -> ROUTING TO: GENERATOR (to fix code bugs)")
        elif decision == "INVALID":
            logger.info(f"\n  -> ROUTING TO: TESTER (to fix tests)")
        elif decision == "VALID_PASS":
            logger.info(f"\n  -> ROUTING TO: REVIEWER (tests passed!)")
        else:
            logger.info(f"\n  -> UNKNOWN DECISION")

        logger.info(f"\nAnalysis:")
        logger.info(f"  {analysis[:500]}...")

        # Show issues found
        test_issues = result.get('test_issues', [])
        code_issues = result.get('code_issues', [])
        recs = result.get('recommendations', [])

        if test_issues:
            logger.info(f"\nTest Issues ({len(test_issues)}):")
            for issue in test_issues[:5]:
                logger.info(f"  - {issue[:150]}")

        if code_issues:
            logger.info(f"\nCode Issues ({len(code_issues)}):")
            for issue in code_issues[:5]:
                logger.info(f"  - {issue[:150]}")

        if recs:
            logger.info(f"\nRecommendations for next agent ({len(recs)}):")
            for rec in recs[:5]:
                logger.info(f"  - {rec[:150]}")

        logger.info(f"\nDuration: {result.get('duration_seconds', 0):.1f}s")
        logger.info(f"Tokens used: {result.get('tokens_used', 0)}")
        logger.info("=" * 70)

        return result

    except Exception as e:
        logger.exception(f"TestReviewerAgent failed with exception: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
