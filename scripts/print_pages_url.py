"""Print the GitHub Pages URL after a successful commit.

Intended to run via pre-commit at the `post-commit` stage.
"""

from __future__ import annotations


PAGES_URL = "https://richardc5168.github.io/ai-math-web/"


def main() -> int:
    print("\nWEB:")
    print(PAGES_URL)
    print("(After `git push origin main`, wait ~1-3 minutes for Pages to update.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
