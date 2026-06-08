"""
Specialized worker agents.

Each agent does one job and reports to the orchestrator. This mirrors the
worker layer in the architecture: Scout finds work, Sentinel assesses risk,
Deployer carries out approved changes.

The agent logic here is deterministic and simulated. The point of this POC
is to demonstrate the coordination and governance pattern, not to perform
real patching. Swapping the simulated logic for real platform integrations
(or a model-backed decision) would not change the orchestration around it.

Standard library only. Runs on Python 3.9+.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

from governance import AuditLog


@dataclass
class Patch:
    """A candidate change Scout has discovered for a system."""
    patch_id: str
    description: str
    risk: str           # "low", "medium", or "high"


@dataclass
class Finding:
    """A security issue Sentinel has detected on a system."""
    finding_id: str
    description: str
    severity: str       # "low", "medium", "high", "critical"


class ScoutAgent:
    """Discovers available patches for a system and rates their risk."""

    name = "Scout"

    _CATALOG = [
        ("SAP-KERNEL-7.53", "SAP HANA kernel security update", "high"),
        ("HANA-REV-067", "HANA platform revision upgrade", "medium"),
        ("OS-PATCH-2026Q2", "Operating system quarterly patch", "low"),
        ("ABAP-NOTE-3344", "ABAP correction note", "low"),
    ]

    def __init__(self, audit: AuditLog, rng: random.Random) -> None:
        self.audit = audit
        self.rng = rng

    def scan(self, system: str) -> List[Patch]:
        count = self.rng.randint(1, 3)
        chosen = self.rng.sample(self._CATALOG, count)
        patches = [Patch(p[0], p[1], p[2]) for p in chosen]
        self.audit.record(self.name, "scan-patches", system,
                          f"{len(patches)} patch(es) found", "ok")
        return patches


class SentinelAgent:
    """Scans a system for vulnerabilities and ranks them by severity."""

    name = "Sentinel"

    _SIGNATURES = [
        ("CVE-2026-1180", "Unauthenticated RFC gateway access", "critical"),
        ("CVE-2026-0921", "Outdated TLS cipher suite", "medium"),
        ("CFG-DRIFT-08", "Configuration drift from baseline", "low"),
    ]

    def __init__(self, audit: AuditLog, rng: random.Random) -> None:
        self.audit = audit
        self.rng = rng

    def scan(self, system: str) -> List[Finding]:
        findings: List[Finding] = []
        for sig in self._SIGNATURES:
            # Roughly a third of signatures fire on any given system.
            if self.rng.random() < 0.34:
                findings.append(Finding(sig[0], sig[1], sig[2]))
        result = f"{len(findings)} finding(s)"
        self.audit.record(self.name, "scan-security", system, result, "ok")
        return findings


class DeployerAgent:
    """Applies an approved patch to a system, tier by tier. Simulates the
    occasional failure so the rollback path is demonstrated, not just claimed."""

    name = "Deployer"

    def __init__(self, audit: AuditLog, rng: random.Random) -> None:
        self.audit = audit
        self.rng = rng

    def apply(self, system: str, patch: Patch) -> bool:
        # Small chance of a failed apply, which must trigger rollback.
        failed = self.rng.random() < 0.12
        if failed:
            self.audit.record(self.name, "apply-patch", system,
                              patch.patch_id, "failed")
            self.audit.record(self.name, "rollback", system,
                              f"{patch.patch_id} reverted to last good state",
                              "rolled back")
            return False
        self.audit.record(self.name, "apply-patch", system,
                          patch.patch_id, "ok")
        return True
