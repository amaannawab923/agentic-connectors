#!/usr/bin/env python3
"""
Manual script to run the reviewer agent on Google Sheets connector code.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.reviewer import ReviewerAgent
from app.models.schemas import GeneratedFile


async def main():
    print("=" * 80)
    print("Running Code Review on Google Sheets Connector")
    print("=" * 80)

    # Define the source directory
    src_dir = Path(__file__).parent / "output/connector-implementations/source-google-sheets/src"

    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}")
        return 1

    # Read all Python files
    print(f"\n[1] Reading connector source files from: {src_dir}")
    generated_files = []

    for py_file in sorted(src_dir.glob("*.py")):
        print(f"    - {py_file.name}")
        with open(py_file, 'r') as f:
            content = f.read()
            generated_files.append(GeneratedFile(
                path=f"src/{py_file.name}",
                content=content
            ))

    print(f"\n    Total files: {len(generated_files)}")

    # Create reviewer agent
    print("\n[2] Initializing reviewer agent...")
    reviewer = ReviewerAgent()

    # Modified system prompt to include severity categorization
    reviewer.system_prompt = """You are a senior software engineer conducting a thorough code review.

Your review should evaluate:

1. **Code Quality**
   - Readability and clarity
   - Naming conventions
   - Code organization
   - DRY principle adherence

2. **Type Safety**
   - Complete type hints
   - Proper use of Optional, Union, etc.
   - Pydantic model usage

3. **Error Handling**
   - Custom exceptions
   - Proper error propagation
   - Meaningful error messages
   - Retry logic

4. **Security**
   - No hardcoded credentials
   - Proper secret handling
   - Input validation
   - No sensitive data in logs

5. **Architecture**
   - Separation of concerns
   - Modularity
   - Clean interfaces
   - Testability

6. **Documentation**
   - Docstrings
   - Comments where needed
   - Clear APIs

Provide specific, actionable feedback with file paths and line references.
Rate the code from 1-10 and categorize comments by severity.

**Severity Levels:**
- **low**: Minor improvements, code style, or documentation suggestions
- **medium**: Important issues that should be fixed but don't block production
- **critical**: Security issues, bugs, or major architectural problems that must be fixed

Output your review in JSON format:
```json
{
    "decision": "approved" | "needs_work" | "rejected",
    "score": <1-10>,
    "summary": "brief summary",
    "comments": [
        {
            "file": "path/to/file.py",
            "line": <number or null>,
            "severity": "low" | "medium" | "critical",
            "message": "comment message",
            "suggestion": "suggested fix or null"
        }
    ],
    "improvements_required": ["improvement 1", "improvement 2"]
}
```"""

    # Execute review
    print("\n[3] Running code review...")
    print("    (This may take a minute...)\n")

    result = await reviewer.execute(
        generated_files=generated_files,
        connector_name="source-google-sheets",
        test_passed=True  # Our test passed (connection worked)
    )

    # Parse and display results
    if not result.success:
        print(f"✗ Review failed: {result.error}")
        return 1

    review_data = json.loads(result.output)

    print("=" * 80)
    print("CODE REVIEW RESULTS")
    print("=" * 80)

    print(f"\n📊 Overall Score: {review_data['score']}/10")
    print(f"📋 Decision: {review_data['decision'].upper()}")
    print(f"⏱️  Duration: {result.duration_seconds:.2f}s")
    print(f"🔤 Tokens Used: {result.tokens_used}")

    print(f"\n📝 Summary:")
    print(f"   {review_data['summary']}")

    # Categorize comments by severity
    comments_by_severity = {
        'critical': [],
        'medium': [],
        'low': []
    }

    for comment in review_data.get('comments', []):
        severity = comment.get('severity', 'low')
        # Map old severity names to new ones
        if severity == 'error':
            severity = 'critical'
        elif severity == 'warning':
            severity = 'medium'
        elif severity == 'info':
            severity = 'low'
        comments_by_severity[severity].append(comment)

    # Display comments by severity
    print("\n" + "=" * 80)
    print("REVIEW COMMENTS BY SEVERITY")
    print("=" * 80)

    # Critical issues
    if comments_by_severity['critical']:
        print(f"\n🔴 CRITICAL ({len(comments_by_severity['critical'])} issues)")
        print("-" * 80)
        for i, comment in enumerate(comments_by_severity['critical'], 1):
            print(f"\n  {i}. File: {comment['file']}")
            if comment.get('line'):
                print(f"     Line: {comment['line']}")
            print(f"     Issue: {comment['message']}")
            if comment.get('suggestion'):
                print(f"     Fix: {comment['suggestion']}")

    # Medium issues
    if comments_by_severity['medium']:
        print(f"\n🟡 MEDIUM ({len(comments_by_severity['medium'])} issues)")
        print("-" * 80)
        for i, comment in enumerate(comments_by_severity['medium'], 1):
            print(f"\n  {i}. File: {comment['file']}")
            if comment.get('line'):
                print(f"     Line: {comment['line']}")
            print(f"     Issue: {comment['message']}")
            if comment.get('suggestion'):
                print(f"     Fix: {comment['suggestion']}")

    # Low priority issues
    if comments_by_severity['low']:
        print(f"\n🟢 LOW ({len(comments_by_severity['low'])} issues)")
        print("-" * 80)
        for i, comment in enumerate(comments_by_severity['low'], 1):
            print(f"\n  {i}. File: {comment['file']}")
            if comment.get('line'):
                print(f"     Line: {comment['line']}")
            print(f"     Issue: {comment['message']}")
            if comment.get('suggestion'):
                print(f"     Fix: {comment['suggestion']}")

    # Improvements required
    if review_data.get('improvements_required'):
        print("\n" + "=" * 80)
        print("IMPROVEMENTS REQUIRED")
        print("=" * 80)
        for i, improvement in enumerate(review_data['improvements_required'], 1):
            print(f"  {i}. {improvement}")

    # Summary stats
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"  Total Comments: {len(review_data.get('comments', []))}")
    print(f"  🔴 Critical: {len(comments_by_severity['critical'])}")
    print(f"  🟡 Medium: {len(comments_by_severity['medium'])}")
    print(f"  🟢 Low: {len(comments_by_severity['low'])}")
    print("=" * 80)

    # Save full review to JSON file
    output_file = Path(__file__).parent / "review_results.json"
    with open(output_file, 'w') as f:
        json.dump(review_data, f, indent=2)
    print(f"\n💾 Full review saved to: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
