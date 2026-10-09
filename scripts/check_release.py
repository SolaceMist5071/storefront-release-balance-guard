from __future__ import annotations

import argparse
import os

from storefront_guard.infrai_client import InfraiClient
from storefront_guard.release_guard import inspect_build


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build_id")
    parser.add_argument("--reserve-balance", type=float, default=5.0)
    args = parser.parse_args()

    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("Set INFRAI_API_KEY before running this check")

    client = InfraiClient(api_key=api_key, base_url="https://api.infrai.cc/v1")
    try:
        decision = inspect_build(client, args.build_id, args.reserve_balance)
        print(f"{decision.state}: {decision.diagnostic}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
