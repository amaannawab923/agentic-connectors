#!/usr/bin/env python3
"""CLI tool for generating smart mocks from connector code.

Usage:
    python cli_mock_generator.py <connector_dir>

Example:
    python cli_mock_generator.py ./output/connector-implementations/source-google-sheets
"""

import sys
from pathlib import Path
from smart_mock_generator import SmartMockGenerator


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python cli_mock_generator.py <connector_dir>")
        print("\nExample:")
        print("  python cli_mock_generator.py ./output/connector-implementations/source-google-sheets")
        sys.exit(1)

    connector_dir = Path(sys.argv[1])

    if not connector_dir.exists():
        print(f"❌ Error: Directory not found: {connector_dir}")
        sys.exit(1)

    print(f"🔍 Analyzing connector at: {connector_dir}")
    print()

    # Generate mocks
    generator = SmartMockGenerator(connector_dir)
    success, result = generator.generate()

    if not success:
        print(f"❌ Error: {result}")
        sys.exit(1)

    print("✅ Mock generation successful!")
    print()

    # Save to file
    output_file = generator.save_to_file(result)
    print(f"📝 Saved to: {output_file}")
    print()

    # Show preview
    print("="*80)
    print("PREVIEW (first 50 lines):")
    print("="*80)
    lines = result.split('\n')[:50]
    for line in lines:
        print(line)
    print()
    print(f"... ({len(result.split(chr(10))) - 50} more lines)")
    print()
    print("✅ Done! You can now use this conftest in your tests.")


if __name__ == "__main__":
    main()
