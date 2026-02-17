"""OpenAI-powered PR review script for GitHub Actions."""
from __future__ import annotations

import json
import os
import sys
import urllib.request

SYSTEM_PROMPT = """\
You are a senior software engineer reviewing the PR diff below.
The project is a Python Textual TUI app (hawaii-disco).

Review based on the following criteria:

## Code Quality
- Bugs, security vulnerabilities, performance issues
- Code style (ruff py311, line-length=120)
- Type hint consistency (from __future__ import annotations)
- Consistency with existing patterns/conventions

## Tests
- Test coverage for changed code
- Missing edge cases
- Test naming conventions

## Documentation
- Whether CLAUDE.md needs updating
- Appropriateness of docstrings/comments
- Whether a CHANGELOG entry is needed

Be concise and focus on substantive issues. Skip trivial style nits.

Respond ONLY in the following JSON format, with no other text:
{
  "review": "Review body in markdown",
  "suggestions": [
    {
      "title": "Concise issue title",
      "label": "bug | enhancement | performance | security | documentation",
      "body": "Issue body in markdown, describing the problem and suggested fix"
    }
  ]
}

Rules:
- suggestions should only include substantive, important items (skip trivial style issues)
- If there are no issues, set suggestions to an empty array
- If there are no issues, set review to "LGTM"
- All output must be in English
"""

VALID_LABELS = {"bug", "enhancement", "performance", "security", "documentation"}


def call_openai(api_key: str, diff: str) -> dict:
    """Call OpenAI API and return parsed JSON response."""
    body = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"--- PR Diff ---\n{diff}"},
        ],
        "max_tokens": 4096,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"OpenAI API error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)

    content = result["choices"][0]["message"]["content"]
    return json.loads(content)


def write_review(review_data: dict, output_path: str) -> None:
    """Write the review comment body to a file."""
    review_text = review_data.get("review", "LGTM")
    suggestions = review_data.get("suggestions", [])

    with open(output_path, "w") as f:
        f.write("## \U0001f916 AI Code Review\n\n")
        f.write(review_text)
        if suggestions:
            f.write(f"\n\n---\n\U0001f4cb **{len(suggestions)} suggestion(s) will be filed as GitHub issues.**")
        f.write("\n\n---\n*Reviewed by GPT-4o*")


def write_suggestions(review_data: dict, output_path: str) -> None:
    """Write validated suggestions to a JSON file for the workflow to consume."""
    suggestions = review_data.get("suggestions", [])

    validated = []
    for s in suggestions:
        title = s.get("title", "").strip()
        label = s.get("label", "enhancement").strip()
        body = s.get("body", "").strip()
        if not title or not body:
            continue
        if label not in VALID_LABELS:
            label = "enhancement"
        validated.append({"title": title, "label": label, "body": body})

    with open(output_path, "w") as f:
        json.dump(validated, f, ensure_ascii=False)

    print(f"{len(validated)} suggestion(s) to create as issues.")


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    diff_path = "/tmp/pr_diff_truncated.txt"
    if not os.path.exists(diff_path):
        print(f"Error: {diff_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(diff_path) as f:
        diff = f.read()

    if not diff.strip():
        with open("/tmp/review_body.txt", "w") as f:
            f.write("## \U0001f916 AI Code Review\n\nNo changes detected.\n")
        with open("/tmp/suggestions.json", "w") as f:
            json.dump([], f)
        return

    review_data = call_openai(api_key, diff)
    write_review(review_data, "/tmp/review_body.txt")
    write_suggestions(review_data, "/tmp/suggestions.json")

    print("Review generated successfully.")


if __name__ == "__main__":
    main()
