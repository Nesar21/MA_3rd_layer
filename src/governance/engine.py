import json
import os
import time
from typing import Dict, Any, List, Optional

from .hashing import GovernanceHasher
from .schema import ARCHITECTURE_CONTRACT_SCHEMA, get_schema_version_hash
from .reviewer import ReviewerGate, ReviewResult

# ---------------------------------------------------------
# GOVERNANCE ENGINE
# ---------------------------------------------------------

class GovernanceEngine:
    """
    The Authority.
    Orchestrates the governance process.
    - Loads Laws (Manifest)
    - Verifies Self-Consistency (Risk #3 Fix)
    - Summons Judge (Reviewer)
    - Issues Decrees (Freeze/Reject)
    """

    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path
        self.manifest = self._load_manifest()
        self.reviewer = ReviewerGate(self.manifest)
        
        # Calculate the immutable Governance Version Hash at startup
        self.governance_version = self._compute_governance_version_hash()

    def _load_manifest(self) -> Dict[str, Any]:
        """
        Loads the system-owned manifest. 
        Planner has NO access to modify this runtime object.
        """
        with open(self.manifest_path, 'r') as f:
            return json.load(f)

    def _compute_governance_version_hash(self) -> str:
        """
        Computes the cryptographically bound version of the Governance Layer.
        Hash = SHA256( Manifest + Schema + ReviewerSourceCode )
        """
        # 1. Manifest Hash
        manifest_canonical = self.manifest

        # 2. Schema Hash
        schema_canonical = ARCHITECTURE_CONTRACT_SCHEMA

        # 3. Reviewer Logic Hash (Proxy for AST)
        reviewer_source_path = os.path.join(os.path.dirname(__file__), 'reviewer.py')
        with open(reviewer_source_path, 'r') as f:
            reviewer_logic_str = f.read()

        return GovernanceHasher.compute_governance_version(
            manifest_canonical,
            schema_canonical,
            reviewer_logic_str
        )

    def _verify_self_consistency(self, plan: Dict[str, Any]) -> Optional[str]:
        """
        Risk #3 Fix: Mandatory Self-Verification.
        Ensures that the Governance Manifest rules don't depend on phantom fields.
        """
        dependencies = self.manifest.get("check_section_dependencies", {})
        
        # Flatten available sections in the plan for lookup
        # We look at Top-Level Keys AND keys inside 'invariants'
        available_sections = set(plan.keys())
        if "invariants" in plan and isinstance(plan["invariants"], dict):
            available_sections.update(plan["invariants"].keys())
            
        for check_id, required_sections in dependencies.items():
            for section in required_sections:
                if section == "*":
                    continue
                if section not in available_sections:
                    return f"Governance Config Error: Check '{check_id}' depends on missing section '{section}'."
        return None

    def evaluate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        The Main Public API.
        Input: Candidate Architecture Contract
        Output: Governance Event (PLAN_FROZEN or PLAN_REJECTED)
        """
        timestamp = int(time.time())

        # 0. PRE-FLIGHT: Self-Consistency Check
        consistency_error = self._verify_self_consistency(plan)
        if consistency_error:
             return {
                "event_type": "PLAN_REJECTED",
                "timestamp": timestamp,
                "governance_version": self.governance_version,
                "status": "FAIL_GOVERNANCE_CONFIG",
                "authority_granted": False,
                "error_count": 1,
                "errors": [{
                    "check_id": "SYS-CONSISTENCY",
                    "section": "manifest",
                    "message": consistency_error,
                    "reference": "manifest.json"
                }],
                "locked_sections": [],
                "remediation": "SYSTEM ERROR: The Governance Manifest requires fields not present in the plan structure."
            }

        # 1. Execute Review
        result: ReviewResult = self.reviewer.evaluate(plan)

        if result.admissible:
            # --- FREEZE PATH ---
            # Authority granted.
            plan_hash = GovernanceHasher.compute_sha256(plan)
            
            return {
                "event_type": "PLAN_FROZEN",
                "timestamp": timestamp,
                "governance_version": self.governance_version,
                "plan_hash": plan_hash,
                "schema_version": plan.get("schema_version"),
                "status": "ADMISSIBLE",
                "authority_granted": True,
                "frozen_artifact": plan 
            }
        
        else:
            # --- REJECT PATH ---
            # Authority denied.
            return {
                "event_type": "PLAN_REJECTED",
                "timestamp": timestamp,
                "governance_version": self.governance_version,
                "status": "REJECTED",
                "authority_granted": False,
                "error_count": len(result.errors),
                "errors": [
                    {
                        "check_id": err.check_id,
                        "section": err.section,
                        "message": err.message,
                        "reference": err.reference
                    } for err in result.errors
                ],
                "locked_sections": result.locked_sections,
                "remediation": "Planner must correct errors without modifying locked sections."
            }