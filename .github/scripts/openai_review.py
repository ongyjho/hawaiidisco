"""OpenAI-powered PR review script for GitHub Actions."""
from __future__ import annotations

import json
import os
import sys
import urllib.request

SYSTEM_PROMPT = """\
당신은 시니어 소프트웨어 엔지니어이고, 아래 PR diff를 리뷰해야 합니다.
프로젝트는 Python Textual TUI 앱(hawaii-disco)입니다.

아래 기준으로 리뷰해주세요:

## 코드 품질
- 버그, 보안 취약점, 성능 이슈
- 코드 스타일 (ruff py311, line-length=120)
- 타입 힌트 일관성 (from __future__ import annotations)
- 기존 패턴/컨벤션과의 일관성

## 테스트
- 변경된 코드에 대한 테스트 커버리지
- 엣지 케이스 누락 여부
- 테스트 네이밍 컨벤션

## 문서
- CLAUDE.md 업데이트 필요 여부
- docstring/주석 적절성
- CHANGELOG 항목 필요 여부

간결하게 핵심만 지적해주세요. 사소한 스타일 이슈보다 실질적 문제에 집중해주세요.
문제가 없으면 "LGTM"이라고만 답해주세요.
"""


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
            f.write("## 🤖 AI Code Review\n\nNo changes detected.\n")
        return

    body = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"--- PR Diff ---\n{diff}"},
        ],
        "max_tokens": 4096,
        "temperature": 0.2,
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

    review = result["choices"][0]["message"]["content"]

    with open("/tmp/review_body.txt", "w") as f:
        f.write("## 🤖 AI Code Review\n\n")
        f.write(review)
        f.write("\n\n---\n*Reviewed by GPT-4o*")

    print("Review generated successfully.")


if __name__ == "__main__":
    main()
