#!/usr/bin/env python3
"""
Manual script to run the publisher agent on Google Sheets connector code.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.publisher import PublisherAgent
from app.models.schemas import GeneratedFile


async def main():
    print("=" * 80)
    print("Publishing Google Sheets Connector to GitHub")
    print("=" * 80)

    # Get user input for repository details
    print("\n📋 Please provide the following information:")
    print("-" * 80)

    repo_owner = input("GitHub Repository Owner: ").strip()
    if not repo_owner:
        print("❌ Repository owner is required!")
        return 1

    repo_name = input("GitHub Repository Name: ").strip()
    if not repo_name:
        print("❌ Repository name is required!")
        return 1

    personal_access_token = input("GitHub Personal Access Token: ").strip()
    if not personal_access_token:
        print("❌ Personal access token is required!")
        return 1

    branch_name = input("Branch Name (press Enter for default 'connector/google-sheets'): ").strip()
    if not branch_name:
        branch_name = "connector/google-sheets"

    print("\n" + "=" * 80)
    print("CONFIGURATION")
    print("=" * 80)
    print(f"Repository: {repo_owner}/{repo_name}")
    print(f"Branch: {branch_name}")
    print(f"Token: {personal_access_token[:4]}...{personal_access_token[-4:]}")

    confirm = input("\n✓ Proceed with publishing? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("❌ Publishing cancelled.")
        return 0

    # Define the source directory
    connector_dir = Path(__file__).parent / "output/connector-implementations/source-google-sheets"

    if not connector_dir.exists():
        print(f"\n❌ Error: Connector directory not found: {connector_dir}")
        return 1

    # Read all connector files
    print(f"\n[1] Reading connector files from: {connector_dir}")
    generated_files = []

    # Read source files
    src_dir = connector_dir / "src"
    if src_dir.exists():
        for py_file in sorted(src_dir.glob("*.py")):
            print(f"    - src/{py_file.name}")
            with open(py_file, 'r') as f:
                content = f.read()
                generated_files.append(GeneratedFile(
                    path=f"src/{py_file.name}",
                    content=content
                ))

    # Read tests
    tests_dir = connector_dir / "tests"
    if tests_dir.exists():
        for py_file in sorted(tests_dir.glob("*.py")):
            print(f"    - tests/{py_file.name}")
            with open(py_file, 'r') as f:
                content = f.read()
                generated_files.append(GeneratedFile(
                    path=f"tests/{py_file.name}",
                    content=content
                ))

    # Read other important files
    for file_name in ["requirements.txt", "README.md", "setup.py"]:
        file_path = connector_dir / file_name
        if file_path.exists():
            print(f"    - {file_name}")
            with open(file_path, 'r') as f:
                content = f.read()
                generated_files.append(GeneratedFile(
                    path=file_name,
                    content=content
                ))

    print(f"\n    Total files: {len(generated_files)}")

    if not generated_files:
        print("\n❌ Error: No connector files found!")
        return 1

    # Create publisher agent
    print("\n[2] Initializing publisher agent...")
    publisher = PublisherAgent()

    # Execute publishing
    print("\n[3] Publishing to GitHub...")
    print("    (This may take a minute...)\n")

    result = await publisher.execute(
        generated_files=generated_files,
        connector_name="google-sheets",
        output_dir=str(connector_dir),
        repo_path=str(connector_dir),
        create_pr=False,  # Just push to branch, don't create PR
        repo_owner=repo_owner,
        repo_name=repo_name,
        personal_access_token=personal_access_token,
        branch_name=branch_name,
    )

    # Display results
    print("\n" + "=" * 80)
    print("PUBLISHING RESULTS")
    print("=" * 80)

    if result.success:
        print(f"\n✅ SUCCESS!")
        print(f"\n📊 Details:")
        print(f"   Duration: {result.duration_seconds:.2f}s")
        print(f"   Tokens Used: {result.tokens_used}")
        print(f"\n📝 Output:")
        print(f"   {result.output}")

        # Try to parse output if it's JSON
        try:
            output_data = json.loads(result.output)
            if "commit_hash" in output_data:
                print(f"\n🔗 Commit Hash: {output_data['commit_hash']}")
            if "branch_name" in output_data:
                print(f"🌿 Branch: {output_data['branch_name']}")
            print(f"\n🔗 View on GitHub:")
            print(f"   https://github.com/{repo_owner}/{repo_name}/tree/{branch_name}")
        except (json.JSONDecodeError, TypeError):
            pass

        print("\n" + "=" * 80)
        print("✅ CONNECTOR PUBLISHED SUCCESSFULLY!")
        print("=" * 80)

        return 0

    else:
        print(f"\n❌ FAILED!")
        print(f"\n📝 Error: {result.error}")

        if result.output:
            print(f"\n📄 Output:")
            print(result.output)

        print("\n" + "=" * 80)
        print("❌ PUBLISHING FAILED")
        print("=" * 80)

        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
