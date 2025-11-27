#!/usr/bin/env python3
"""Test script for MockGeneratorAgent.

This script tests the MockGeneratorAgent on the Google Sheets connector
to validate it can generate accurate API mock fixtures.

Usage:
    python test_mock_agent.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents import MockGeneratorAgent
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_mock_generator():
    """Test the MockGeneratorAgent on Google Sheets connector."""

    logger.info("=" * 80)
    logger.info("Testing MockGeneratorAgent on Google Sheets Connector")
    logger.info("=" * 80)

    # Initialize settings
    settings = get_settings()

    # Create the agent
    agent = MockGeneratorAgent(settings=settings)

    # Connector details
    connector_name = "google-sheets"
    connector_type = "source"

    # Check if connector exists
    connector_dir = Path("output/connector-implementations") / f"{connector_type}-{connector_name}"
    if not connector_dir.exists():
        logger.error(f"Connector directory not found: {connector_dir}")
        logger.error("Please run the generator first to create the connector.")
        return False

    # Check if IMPLEMENTATION.md exists
    impl_file = connector_dir / "IMPLEMENTATION.md"
    if not impl_file.exists():
        logger.warning(f"IMPLEMENTATION.md not found at {impl_file}")
    else:
        logger.info(f"✅ Found IMPLEMENTATION.md at {impl_file}")

    # Check if client.py exists
    client_file = connector_dir / "src" / "client.py"
    if not client_file.exists():
        logger.error(f"client.py not found at {client_file}")
        return False
    else:
        logger.info(f"✅ Found client.py at {client_file}")

    # Read client methods (simple extraction)
    try:
        client_code = client_file.read_text()
        import re
        methods = re.findall(r'def\s+(\w+)\s*\(', client_code)
        # Filter out private methods and __init__
        client_methods = [m for m in methods if not m.startswith('_')]
        logger.info(f"✅ Found {len(client_methods)} public methods in client: {client_methods}")
    except Exception as e:
        logger.warning(f"Could not extract methods: {e}")
        client_methods = None

    # Prepare research summary (optional - could be loaded from file)
    research_summary = """
Google Sheets API v4 Documentation:
- REST API: https://developers.google.com/sheets/api/reference/rest
- Authentication: OAuth2 or Service Account
- Main resources: Spreadsheets, Values, Metadata
- Common operations: get, batchGet, update, append
- Rate limits: 100 requests per 100 seconds per user
"""

    logger.info("\n" + "=" * 80)
    logger.info("Starting MockGeneratorAgent execution...")
    logger.info("=" * 80 + "\n")

    # Execute the agent
    try:
        result = await agent.execute(
            connector_name=connector_name,
            connector_type=connector_type,
            research_summary=research_summary,
            client_methods=client_methods
        )

        logger.info("\n" + "=" * 80)
        logger.info("MockGeneratorAgent Execution Complete")
        logger.info("=" * 80)

        if result.success:
            logger.info("✅ SUCCESS!")
            logger.info(f"Message: {result.message}")
            if result.output:
                logger.info(f"\nOutput:")
                for key, value in result.output.items():
                    logger.info(f"  {key}: {value}")

            # Verify fixtures were created
            fixtures_dir = connector_dir / "tests" / "fixtures"
            if fixtures_dir.exists():
                fixture_files = list(fixtures_dir.rglob("*.json"))
                logger.info(f"\n📁 Fixture files created ({len(fixture_files)}):")
                for fixture_file in sorted(fixture_files):
                    rel_path = fixture_file.relative_to(connector_dir)
                    logger.info(f"  - {rel_path}")

            # Check conftest.py
            conftest_path = connector_dir / "tests" / "conftest.py"
            if conftest_path.exists():
                logger.info(f"\n✅ conftest.py created at {conftest_path}")
                # Show first 50 lines
                lines = conftest_path.read_text().split('\n')[:50]
                logger.info("\nFirst 50 lines of conftest.py:")
                logger.info("-" * 80)
                for line in lines:
                    logger.info(line)
                logger.info("-" * 80)

            return True
        else:
            logger.error("❌ FAILED!")
            logger.error(f"Error: {result.error}")
            logger.error(f"Message: {result.message}")
            return False

    except Exception as e:
        logger.error(f"❌ Exception during execution: {e}", exc_info=True)
        return False


def main():
    """Main entry point."""
    try:
        success = asyncio.run(test_mock_generator())
        if success:
            logger.info("\n🎉 MockGeneratorAgent test completed successfully!")
            sys.exit(0)
        else:
            logger.error("\n💥 MockGeneratorAgent test failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n💥 Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
