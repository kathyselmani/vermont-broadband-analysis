"""Command-line entry point: `vermont-broadband-analysis <step>`.

Steps run in order with `all`: profile -> build -> metrics -> providers -> census ->
socioeconomic -> dashboard. The census-dependent steps are skipped with
`all --skip-census`.
"""

import argparse

STEPS = [
    "profile",
    "build",
    "metrics",
    "providers",
    "census",
    "socioeconomic",
    "dashboard",
]


def run_step(step: str, refresh: bool = False) -> None:
    from . import census, dashboard_data, fcc, metrics, providers, socioeconomic

    {
        "profile": fcc.profile,
        "build": fcc.build,
        "metrics": metrics.run,
        "providers": providers.run,
        "census": lambda: census.run(refresh=refresh),
        "socioeconomic": socioeconomic.run,
        "dashboard": dashboard_data.run,
    }[step]()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="vermont-broadband-analysis", description=__doc__
    )
    parser.add_argument("step", choices=STEPS + ["all"])
    parser.add_argument(
        "--skip-census", action="store_true", help="skip census and socioeconomic steps"
    )
    parser.add_argument(
        "--refresh", action="store_true", help="re-download cached Census files"
    )
    args = parser.parse_args()

    steps = STEPS if args.step == "all" else [args.step]
    if args.skip_census:
        steps = [s for s in steps if s not in ("census", "socioeconomic")]
    for step in steps:
        print(f"\n=== {step} ===")
        run_step(step, refresh=args.refresh)
