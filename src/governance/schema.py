import hashlib
import jcs
from typing import List

# ---------------------------------------------------------
# CONSTANTS: REQUIRED DOMAINS (HARD-CODED AS PER SPEC)
# ---------------------------------------------------------

REQUIRED_INVARIANT_DOMAINS: List[str] = [
    "api_contracts",
    "data_schemas",
    "env_vars",
    "build_dependencies",
    "auth_model",
    "persistence_model"
]

REQUIRED_ASSUMPTION_CATEGORIES: List[str] = [
    "authentication",
    "authorization",
    "deployment_scope",
    "data_retention",
    "scaling_model"
]

# ---------------------------------------------------------
# THE SCHEMA AST (ABSTRACT SYNTAX TREE)
# ---------------------------------------------------------

ARCHITECTURE_CONTRACT_SCHEMA = {
    "type": "object",
    "required": ["project_name", "schema_version", "invariants", "assumptions", "build_dag"],
    "additionalProperties": False,
    "properties": {
        "project_name": {"type": "string", "minLength": 1},
        "schema_version": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        
        "invariants": {
            "type": "object",
            "required": REQUIRED_INVARIANT_DOMAINS,
            "additionalProperties": False,
            "properties": {
                domain: {
                    "type": ["object", "array", "string"]
                    # We accept weak structural types here; 
                    # specific emptiness checks are handled by logic, not JSON Schema
                } for domain in REQUIRED_INVARIANT_DOMAINS
            }
        },

        "assumptions": {
            "type": "object",
            "required": REQUIRED_ASSUMPTION_CATEGORIES,
            "additionalProperties": False,
            "properties": {
                category: {
                    "type": "string"
                } for category in REQUIRED_ASSUMPTION_CATEGORIES
            }
        },

        "build_dag": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "string"}
            }
        }
    }
}

# ---------------------------------------------------------
# SELF-VERIFICATION LOGIC
# ---------------------------------------------------------

def get_schema_version_hash() -> str:
    """
    Derives the schema version from the Schema AST itself.
    This prevents 'Liars Version' attacks.
    """
    # We must exclude 'schema_version' definition from the hash 
    # to avoid a recursive paradox, but technically the schema *structure*
    # excluding the value matches is what matters.
    # For simplicity in this strict governance model, we hash the 
    # full dictionary structure defined above.
    
    canonical_bytes = jcs.canonicalize(ARCHITECTURE_CONTRACT_SCHEMA)
    return hashlib.sha256(canonical_bytes).hexdigest()