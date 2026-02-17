"""CLI tool to validate locale YAML files against the English reference.

Usage::

    python -m hawaiidisco.i18n.validate          # validate all locales
    python -m hawaiidisco.i18n.validate ja        # validate Japanese only
    python -m hawaiidisco.i18n.validate ja zh-CN  # validate specific locales
"""
from __future__ import annotations

import sys

from hawaiidisco.i18n import get_available_languages, validate_locale


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if args:
        codes = args
    else:
        codes = [c for c in get_available_languages() if c != "en"]

    if not codes:
        print("No locale files found to validate.")
        return 0

    all_ok = True

    for code in codes:
        result = validate_locale(code)

        if "error" in result:
            print(f"\n[ERROR] {code}: {result['error']}")
            all_ok = False
            continue

        coverage = result["coverage_pct"]
        status = "OK" if coverage == 100.0 else "INCOMPLETE"
        print(f"\n=== {code} ({status}) — {coverage}% coverage ===")

        if result["missing"]:
            print(f"  Missing keys ({len(result['missing'])}):")
            for k in result["missing"]:
                print(f"    - {k}")

        if result["empty"]:
            print(f"  Empty values ({len(result['empty'])}):")
            for k in result["empty"]:
                print(f"    - {k}")

        if result["placeholder_mismatch"]:
            print(f"  Placeholder mismatches ({len(result['placeholder_mismatch'])}):")
            for k in result["placeholder_mismatch"]:
                print(f"    - {k}")

        if result["extra"]:
            print(f"  Extra keys ({len(result['extra'])}):")
            for k in result["extra"]:
                print(f"    - {k}")

        if result["missing"] or result["empty"] or result["placeholder_mismatch"]:
            all_ok = False

    print()
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
