"""
Entry point for the AI-orchestrated operations POC.

Run it:
    python3 main.py

Optional, to make the human approval decisions yourself instead of using the
simulated approver:
    python3 main.py --interactive

No third-party packages. Standard library only. Python 3.9+.
"""

from __future__ import annotations

import sys

from orchestrator import Maestro, System


def build_estate():
    """A small SAP HANA estate across three network tiers."""
    return [
        System("HANA-DEV-01", "Tier 1 (Dev/Test)"),
        System("HANA-DEV-02", "Tier 1 (Dev/Test)"),
        System("HANA-QA-01", "Tier 2 (QA)"),
        System("HANA-PRD-01", "Tier 3 (Prod)"),
        System("HANA-PRD-02", "Tier 3 (Prod)"),
    ]


def main() -> None:
    interactive = "--interactive" in sys.argv

    print("AI-Orchestrated Operations Pipeline (proof of concept)")
    print("Maestro orchestrating Scout, Sentinel, and Deployer across "
          "three tiers.\n")
    print("Legend: lower tiers run first; production and high-risk changes "
          "require a logged human approval.")

    maestro = Maestro(seed=8, interactive=interactive)
    maestro.run(build_estate())

    maestro.audit.export("audit_log.json")
    print("\nFull audit trail written to audit_log.json")


if __name__ == "__main__":
    main()
