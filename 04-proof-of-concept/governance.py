"""
Governance layer for the AI-orchestrated operations POC.

This is where the "human stays in control" part of the architecture lives.
Two pieces:

  - AuditLog: an append-only record of every action any agent takes, so
    nothing happens in a black box.
  - ApprovalGate: a checkpoint that requires explicit human sign-off before
    any high-risk action (in particular, anything touching production).

Standard library only. Runs on Python 3.9+.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional


@dataclass
class AuditEntry:
    """A single immutable record of something that happened."""
    timestamp: str
    actor: str          # which agent or human took the action
    action: str         # what they did
    target: str         # what they did it to
    detail: str         # human-readable context
    result: str         # outcome (e.g. "ok", "denied", "rolled back")


class AuditLog:
    """Append-only audit trail. Writes to the console as it goes and can be
    exported to JSON for compliance review."""

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []

    def record(self, actor: str, action: str, target: str,
               detail: str, result: str) -> None:
        entry = AuditEntry(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            actor=actor,
            action=action,
            target=target,
            detail=detail,
            result=result,
        )
        self._entries.append(entry)
        print(f"  [{entry.timestamp}] {actor:<10} {action:<18} "
              f"{target:<14} {detail} -> {result}")

    def export(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump([asdict(e) for e in self._entries], f, indent=2)

    def __len__(self) -> int:
        return len(self._entries)


class ApprovalGate:
    """Human-in-the-loop checkpoint.

    Policy: any action whose risk is 'high', or any action targeting a
    production tier, requires explicit human approval before it proceeds.
    Everything else passes automatically and is still logged.

    By default the gate runs with a simulated approver so the POC executes
    end to end without stopping for input. Set interactive=True to be
    prompted for the decision yourself.
    """

    def __init__(self, audit: AuditLog, interactive: bool = False,
                 approver_name: str = "change-advisory-board") -> None:
        self.audit = audit
        self.interactive = interactive
        self.approver_name = approver_name

    def requires_approval(self, risk: str, tier_is_production: bool) -> bool:
        return risk == "high" or tier_is_production

    def request(self, action: str, target: str, risk: str,
                tier_is_production: bool) -> bool:
        """Return True if the action is approved, False if denied."""
        if not self.requires_approval(risk, tier_is_production):
            self.audit.record("gate", "auto-approve", target,
                               f"{action} (risk={risk})", "approved")
            return True

        if self.interactive:
            answer = input(f"  APPROVAL REQUIRED: {action} on {target} "
                           f"(risk={risk}). Approve? [y/N] ").strip().lower()
            approved = answer == "y"
        else:
            # Simulated change-advisory decision. Policy: defer (deny) any
            # change that is BOTH high-risk AND targeting production to a
            # scheduled maintenance window. Approve everything else, always
            # with a named approver on record. A real deployment would route
            # this to a person or a change-advisory-board workflow.
            approved = not (risk == "high" and tier_is_production)

        decision = "approved" if approved else "denied"
        self.audit.record(self.approver_name, "human-decision", target,
                           f"{action} (risk={risk})", decision)
        return approved
