import re
import jsonschema
from typing import Dict, List, Any, Set, Tuple, Optional
from dataclasses import dataclass, field

from .schema import ARCHITECTURE_CONTRACT_SCHEMA, get_schema_version_hash

@dataclass
class ReviewError:
    check_id: str
    section: str
    message: str
    reference: Optional[str] = None

@dataclass
class ReviewResult:
    admissible: bool
    errors: List[ReviewError] = field(default_factory=list)
    locked_sections: List[str] = field(default_factory=list)

class ReviewerGate:
    """
    The Mechanical Judge.
    Enforces the rules defined in the Governance Manifest.
    """

    def __init__(self, manifest: Dict[str, Any]):
        self.manifest = manifest
        self.max_errors = manifest.get("max_errors", 5)
        self.weak_format_rules = manifest.get("weak_format_allowlists", {})
        
        # Risk #2 Fix: Protocol-agnostic syntactic validation
        # Allows 'http://', 'ftp://', 'postgres://' etc. 
        self.regex_url = re.compile(r'^(?:[a-z][a-z0-9+.-]*://[\w.-]+|N/A).*')
        
        self.regex_module = re.compile(r'^[a-zA-Z0-9_.]+$') 
        self.regex_package = re.compile(r'^[a-zA-Z0-9_-]+$')
        
        # RG-REFERENCE-003: Strict Identifier Grammar
        # Keys in referenceable domains must be clean (no spaces, no weird chars)
        self.regex_identifier = re.compile(r'^[a-zA-Z0-9_-]+$')

    def evaluate(self, contract: Dict[str, Any]) -> ReviewResult:
        """
        Main entry point. Runs all checks deterministically.
        """
        errors: List[ReviewError] = []
        
        # 1. Schema Validation (RG-SCHEMA-001)
        errors.extend(self._check_schema(contract))

        # Stop early if schema is broken (cannot trust structure)
        if errors:
            return ReviewResult(
                admissible=False, 
                errors=errors[:self.max_errors], 
                locked_sections=[]
            )

        # 2. Invariant & Assumption Presence (RG-INVARIANT-002)
        if len(errors) < self.max_errors:
            errors.extend(self._check_invariants(contract))

        # 3. Reference & Identifier Integrity (RG-REFERENCE-003) - [NOW IMPLEMENTED]
        if len(errors) < self.max_errors:
            errors.extend(self._check_references(contract))

        # 4. Weak Format Validation (RG-WEAK-FORMAT-005)
        if len(errors) < self.max_errors:
            errors.extend(self._check_weak_formats(contract))

        # 5. DAG Validation (RG-DAG-004)
        if len(errors) < self.max_errors:
            errors.extend(self._check_dag(contract))

        # 6. Compute Locked Sections
        locked = self._compute_locked_sections(contract, errors)

        return ReviewResult(
            admissible=(len(errors) == 0),
            errors=errors[:self.max_errors],
            locked_sections=locked
        )

    def _check_schema(self, contract: Dict[str, Any]) -> List[ReviewError]:
        errors = []
        expected_version = get_schema_version_hash()
        declared_version = contract.get("schema_version")
        
        if declared_version != expected_version:
            errors.append(ReviewError(
                check_id="RG-SCHEMA-001",
                section="schema_version",
                message=f"Version mismatch. Expected {expected_version}, got {declared_version}"
            ))

        validator = jsonschema.Draft7Validator(ARCHITECTURE_CONTRACT_SCHEMA)
        for err in validator.iter_errors(contract):
            errors.append(ReviewError(
                check_id="RG-SCHEMA-001",
                section="structure",
                message=err.message,
                reference=str(err.path)
            ))
            if len(errors) >= self.max_errors:
                break
        return errors

    def _check_invariants(self, contract: Dict[str, Any]) -> List[ReviewError]:
        errors = []
        invariants = contract.get("invariants", {})
        for domain, content in invariants.items():
            is_empty = False
            if isinstance(content, str):
                if len(content.strip()) == 0: is_empty = True
            elif isinstance(content, (dict, list)):
                if len(content) == 0: is_empty = True
            elif content is None:
                is_empty = True
            
            if is_empty:
                errors.append(ReviewError(
                    check_id="RG-INVARIANT-002",
                    section=f"invariants.{domain}",
                    message="Domain is declared but empty. Must have at least one entry/character."
                ))
        return errors

    def _check_references(self, contract: Dict[str, Any]) -> List[ReviewError]:
        """
        RG-REFERENCE-003: Enforces strict identifier grammar on referenceable domains.
        """
        errors = []
        invariants = contract.get("invariants", {})
        target_domains = ["api_contracts", "data_schemas"]
        
        for domain in target_domains:
            section = invariants.get(domain)
            if isinstance(section, dict):
                for key in section.keys():
                    if not self.regex_identifier.match(key):
                        errors.append(ReviewError(
                            check_id="RG-REFERENCE-003",
                            section=f"invariants.{domain}",
                            message=f"Invalid identifier format '{key}'. Must match ^[a-zA-Z0-9_-]+$",
                            reference=key
                        ))
        return errors

    def _check_weak_formats(self, contract: Dict[str, Any]) -> List[ReviewError]:
        errors = []
        invariants = contract.get("invariants", {})
        
        def scan_and_validate(data: Any, target_keys: List[str], regex: re.Pattern, label: str):
            if isinstance(data, dict):
                for k, v in data.items():
                    if k in target_keys and isinstance(v, str):
                        if not regex.match(v):
                             errors.append(ReviewError(
                                check_id="RG-WEAK-FORMAT-005",
                                section=f"weak_format.{label}",
                                message=f"Value '{v}' invalid for field '{k}'",
                                reference=k
                            ))
                    else:
                        scan_and_validate(v, target_keys, regex, label)
            elif isinstance(data, list):
                for item in data:
                    scan_and_validate(item, target_keys, regex, label)

        scan_and_validate(invariants, self.weak_format_rules.get("url_fields", []), self.regex_url, "url")
        scan_and_validate(invariants, self.weak_format_rules.get("module_path_fields", []), self.regex_module, "module")
        scan_and_validate(invariants, self.weak_format_rules.get("package_name_fields", []), self.regex_package, "package")
        return errors

    def _check_dag(self, contract: Dict[str, Any]) -> List[ReviewError]:
        errors = []
        dag = contract.get("build_dag", {})
        if not dag:
            return []

        # RG-DAG-004 Part 2: Existence Check (The Hardening)
        build_deps = contract.get("invariants", {}).get("build_dependencies", {})
        valid_nodes = set(build_deps.keys()) if isinstance(build_deps, dict) else set()

        for node in dag.keys():
            if node not in valid_nodes:
                errors.append(ReviewError(
                    check_id="RG-DAG-004",
                    section="build_dag",
                    message=f"DAG node '{node}' is not defined in 'build_dependencies'.",
                    reference=node
                ))
            for target in dag[node]:
                if target not in valid_nodes:
                    errors.append(ReviewError(
                        check_id="RG-DAG-004",
                        section="build_dag",
                        message=f"DAG target '{target}' (referenced by '{node}') is not defined in 'build_dependencies'.",
                        reference=target
                    ))
        
        if errors:
            return errors

        # Cycle Detection
        visited = set()
        recursion_stack = set()
        def detect_cycle(node):
            visited.add(node)
            recursion_stack.add(node)
            neighbors = dag.get(node, [])
            for neighbor in neighbors:
                if neighbor not in visited:
                    if detect_cycle(neighbor): return True
                elif neighbor in recursion_stack: return True
            recursion_stack.remove(node)
            return False

        for node in dag.keys():
            if node not in visited:
                if detect_cycle(node):
                    errors.append(ReviewError(
                        check_id="RG-DAG-004",
                        section="build_dag",
                        message=f"Cycle detected involving node '{node}'",
                        reference=node
                    ))
                    break
        return errors

    def _compute_locked_sections(self, contract: Dict[str, Any], errors: List[ReviewError]) -> List[str]:
        candidates = set(contract.get("invariants", {}).keys())
        candidates.add("build_dag")
        candidates.add("assumptions")
        tainted = set()
        for err in errors:
            parts = err.section.split('.')
            if parts[0] == 'invariants' and len(parts) > 1:
                tainted.add(parts[1])
            elif parts[0] == 'weak_format':
                return []
            elif parts[0] in candidates:
                tainted.add(parts[0])
            else:
                return []
        return list(candidates - tainted)