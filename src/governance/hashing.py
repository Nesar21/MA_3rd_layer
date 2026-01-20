import hashlib
import jcs  # RFC 8785 implementation
from typing import Dict, Any

class GovernanceHasher:
    """
    Implements RFC 8785 Canonicalization to ensure cryptographic
    reproducibility of plans and governance states.
    """

    @staticmethod
    def canonicalize(data: Dict[str, Any]) -> bytes:
        """
        Returns the RFC 8785 canonical bytes of a dictionary.
        This handles key sorting, spacing, and float representation deterministically.
        """
        try:
            return jcs.canonicalize(data)
        except Exception as e:
            # Governance must fail hard on serialization errors
            raise ValueError(f"Canonicalization failed: {str(e)}")

    @staticmethod
    def compute_sha256(data: Dict[str, Any]) -> str:
        """
        Returns the SHA256 hex digest of the canonicalized data.
        """
        canonical_bytes = GovernanceHasher.canonicalize(data)
        return hashlib.sha256(canonical_bytes).hexdigest()

    @staticmethod
    def compute_governance_version(
        manifest: Dict[str, Any],
        schema_ast: Dict[str, Any],
        reviewer_logic_version: str
    ) -> str:
        """
        Computes the Immutable Governance Version Hash.
        Formula: SHA256( canonical(Manifest) + canonical(Schema) + ReviewerLogicString )
        """
        manifest_bytes = GovernanceHasher.canonicalize(manifest)
        schema_bytes = GovernanceHasher.canonicalize(schema_ast)
        logic_bytes = reviewer_logic_version.encode('utf-8')

        # Combined hash for total system state
        hasher = hashlib.sha256()
        hasher.update(manifest_bytes)
        hasher.update(schema_bytes)
        hasher.update(logic_bytes)
        
        return hasher.hexdigest()