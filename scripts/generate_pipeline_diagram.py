#!/usr/bin/env python3
"""Generate PNG diagram of the LangGraph pipeline.

This script generates both a Mermaid text file and PNG image of the pipeline.

Usage:
    python scripts/generate_pipeline_diagram.py [--output-dir ./docs]
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_diagram(output_dir: Path) -> None:
    """Generate pipeline diagram in Mermaid and PNG formats.

    Args:
        output_dir: Directory to save the output files.
    """
    from app.orchestrator.pipeline import build_pipeline

    print("Building pipeline graph...")
    workflow = build_pipeline()
    app = workflow.compile()
    graph = app.get_graph()

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate Mermaid text
    mermaid_text = graph.draw_mermaid()
    mermaid_path = output_dir / "pipeline_v2.mmd"
    mermaid_path.write_text(mermaid_text)
    print(f"Mermaid diagram saved to: {mermaid_path}")

    # Try to generate PNG
    png_path = output_dir / "pipeline_v2.png"

    try:
        # Try using the API method (uses mermaid.ink)
        png_bytes = graph.draw_mermaid_png()
        png_path.write_bytes(png_bytes)
        print(f"PNG diagram saved to: {png_path}")

    except Exception as e:
        print(f"Warning: Could not generate PNG via API: {e}")
        print("Trying alternative method...")

        try:
            # Try using pyppeteer if available
            from langgraph.graph.graph import MermaidDrawMethod
            png_bytes = graph.draw_mermaid_png(draw_method=MermaidDrawMethod.PYPPETEER)
            png_path.write_bytes(png_bytes)
            print(f"PNG diagram saved to: {png_path}")

        except Exception as e2:
            print(f"Warning: Could not generate PNG via pyppeteer: {e2}")
            print("\nTo generate PNG manually, use the Mermaid Live Editor:")
            print("  1. Open https://mermaid.live/")
            print(f"  2. Paste contents of {mermaid_path}")
            print("  3. Export as PNG")

    # Print the Mermaid diagram to console
    print("\n" + "=" * 60)
    print("PIPELINE v2 MERMAID DIAGRAM")
    print("=" * 60)
    print(mermaid_text)
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate PNG diagram of the LangGraph pipeline"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./docs/diagrams"),
        help="Output directory for diagram files (default: ./docs/diagrams)",
    )

    args = parser.parse_args()

    try:
        generate_diagram(args.output_dir)
        print("\nDiagram generation complete!")
        return 0
    except Exception as e:
        print(f"Error generating diagram: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
