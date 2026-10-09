"""Retired Ministry of Culture source-job entrypoint: NO HTTP / DB writes.

Kept as a fail-closed compatibility entrypoint for existing Cloud Run Jobs.
The direct ChatGPT-to-curated-pool flow superseded source Jobs in 2026-10.
"""


def main() -> None:
    raise SystemExit("RETIRED_SOURCE_BATCH: do not run old event collectors")


if __name__ == "__main__":
    main()
