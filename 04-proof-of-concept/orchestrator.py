"""
Maestro: the orchestrator.

Maestro owns the plan. For each system, lowest environment tier first, it:
  1. asks Scout what patches are available,
  2. asks Sentinel what security findings exist,
  3. routes every change through the approval gate (production and high-risk
     changes require a logged human decision),
  4. has Deployer apply approved changes, handling failures with rollback,
  5. records everything to the audit log and reports a summary.

This is the coordination layer. The agents do the work; Maestro decides what
runs, in what order, and what needs a human.

Standard library only. Runs on Python 3.9+.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List

from agents import ScoutAgent, SentinelAgent, DeployerAgent
from governance import AuditLog, ApprovalGate


@dataclass
class System:
    """A target system in the estate."""
    name: str
    tier: str           # "Tier 1 (Dev/Test)", "Tier 2 (QA)", "Tier 3 (Prod)"

    @property
    def is_production(self) -> bool:
        return "Prod" in self.tier


class Maestro:
    """The orchestrator agent."""

    name = "Maestro"

    def __init__(self, seed: int = 7, interactive: bool = False) -> None:
        rng = random.Random(seed)
        self.audit = AuditLog()
        self.gate = ApprovalGate(self.audit, interactive=interactive)
        self.scout = ScoutAgent(self.audit, rng)
        self.sentinel = SentinelAgent(self.audit, rng)
        self.deployer = DeployerAgent(self.audit, rng)
        self.summary: Dict[str, int] = {
            "systems": 0, "patches_found": 0, "applied": 0,
            "denied": 0, "rolled_back": 0, "critical_findings": 0,
        }

    def run(self, systems: List[System]) -> None:
        # Process lower tiers before production. Sorting by tier name works
        # because the tiers are numbered.
        for system in sorted(systems, key=lambda s: s.tier):
            self._process(system)
        self._print_summary()

    def _process(self, system: System) -> None:
        print(f"\n=== {system.name}  [{system.tier}] ===")
        self.summary["systems"] += 1

        # 1. Discover work.
        patches = self.scout.scan(system.name)
        self.summary["patches_found"] += len(patches)

        # 2. Assess security posture.
        findings = self.sentinel.scan(system.name)
        for f in findings:
            if f.severity == "critical":
                self.summary["critical_findings"] += 1
                self.audit.record(self.name, "escalate", system.name,
                                  f"{f.finding_id} ({f.severity})",
                                  "flagged to on-call")

        # 3 + 4. Gate and apply each patch.
        for patch in patches:
            approved = self.gate.request(
                action=f"apply {patch.patch_id}",
                target=system.name,
                risk=patch.risk,
                tier_is_production=system.is_production,
            )
            if not approved:
                self.summary["denied"] += 1
                continue
            ok = self.deployer.apply(system.name, patch)
            if ok:
                self.summary["applied"] += 1
            else:
                self.summary["rolled_back"] += 1

    def _print_summary(self) -> None:
        s = self.summary
        print("\n" + "=" * 52)
        print("RUN SUMMARY")
        print("=" * 52)
        print(f"  Systems processed     : {s['systems']}")
        print(f"  Patches discovered    : {s['patches_found']}")
        print(f"  Patches applied       : {s['applied']}")
        print(f"  Changes denied at gate: {s['denied']}")
        print(f"  Failed + rolled back  : {s['rolled_back']}")
        print(f"  Critical findings     : {s['critical_findings']}")
        print(f"  Audit entries written : {len(self.audit)}")
