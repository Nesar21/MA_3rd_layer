# Marathon Agent — Layer 3: Governance & Safety

**Constitutional admissibility gate and deterministic safety enforcement**

---

## Overview

**Marathon Agent** is a production-oriented AI execution framework designed for:

- quota-aware execution  
- deterministic interruption & resume  
- audit-safe artifact generation  
- strict separation of authority and reasoning  

**Layer 3 (Governance & Safety)** functions as the *constitutional gatekeeper* of the system.

It sits **between**:

- **Layer 2 — Planning (Untrusted AI Output)**
- **Layer 4 — Code Generation (Expensive & Destructive)**

Its purpose is singular and non-negotiable:

> **Reject architecturally invalid plans before they consume compute or corrupt downstream execution.**

Layer 3 operates under a **Zero-Trust model**:  
The Planner is treated as an untrusted entity whose output must be proven admissible against a rigid, system-owned constitution.

---

## Layer 3 Mission Statement

Layer 3 answers **one question only**:

> **“Is this plan admissible for downstream execution under the declared constitution?”**

It explicitly **refuses** to answer:

- Is the plan good?
- Is the plan useful?
- Is the plan correct?
- Is the plan executable?

**Admissible ≠ Viable ≠ Correct**

This separation is intentional and enforced.

---

## Responsibilities

Layer 3 is responsible for:

- **Constitutional Enforcement**  
  Validate plans against immutable system laws (`manifest.json`)

- **Authority Granting**  
  Transition plans from `DRAFT` → `FROZEN`

- **Structural Integrity**  
  Enforce schema versioning, reference syntax, and DAG safety

- **Forensic Rejection**  
  Produce immutable, structured rejection artifacts

- **Replay Safety**  
  Ensure deterministic behavior using RFC 8785 canonical hashing

---

## Explicit Non-Responsibilities

Layer 3 **does not**:

- Fix planner mistakes  
- Infer intent  
- Perform semantic reasoning  
- Execute code  
- Validate correctness  
- Interact with users  
- Adapt behavior across runs  

Layer 3 enforces **admissibility**, not **utility**.

---

## Authority Model

### Authority Rule

A plan has **zero execution authority** until it is frozen.

Plans exist in exactly three states:

| State      | Description                                   | Authority |
|------------|-----------------------------------------------|-----------|
| `DRAFT`    | Planner output                                | ❌ None |
| `REJECTED` | Preserved for audit                           | ❌ None |
| `FROZEN`   | Constitutionally admissible                   | ✅ Granted |

> **Freeze is the only authority transition.**  
> Existence does not imply authority.

---

## The Constitution (Governance Manifest)

Governance rules are defined in a **system-owned JSON artifact**:

src/governance/manifest.json


### Properties

- Not planner-authored  
- Not user-editable  
- Loaded from sealed code path  
- Immutable per execution  

If the planner could influence governance rules, governance would be meaningless.  
This is explicitly forbidden.

---

## Inputs & Outputs

### Inputs (Read-Only)

- Architecture Contract (JSON)
- Governance Manifest (JSON)
- Progress Ledger (limited read only)

### Outputs (Single Event)

Exactly one of:

- `PLAN_FROZEN`
- `PLAN_REJECTED`
- `FAILURE_RETRY_EXHAUSTED`

No partial authority.  
No silent downgrade.

---

## Governance Versioning & Replay Safety

### Governance Hash

Governance identity is derived from:

- Canonicalized Reviewer Gate AST  
- Canonicalized Schema AST  
- Canonicalized Governance Manifest  

Using **RFC 8785 (JSON Canonicalization Scheme)**.

Hashing is **structure-based**, not text-based.

Any change → new governance hash → resume invalidation is expected and allowed.

> Governance evolution invalidates prior admissibility guarantees.  
> This is an owned trade-off.

---

## Mechanical Checks (No Semantics)

Every plan must pass **all enabled checks**.

### RG-SCHEMA-001 — Structural Validity

- JSON schema validation  
- Schema version derived from schema AST  
- Exact match required  

No schema → no governance.

---

### RG-INVARIANT-002 — Domain Presence

Required invariant domains must exist and be non-empty.

**Non-empty definition (mechanical):**

- string → length ≥ 1 after trim  
- object → ≥ 1 key  
- array → ≥ 1 element  

> Completeness means **explicit declaration**, not adequacy or correctness.

---

### RG-REFERENCE-003 — Exact Reference Resolution

- Identifiers must match declared entities  
- Exact byte-for-byte match  
- Case-sensitive  
- Regex-enforced grammar  
- No fuzzy matching  

Typos fail fast.  
Planner retry handles correction.

---

### RG-DAG-004 — Build DAG Validity

- All nodes must exist  
- Identifiers canonicalized  
- DAG must be acyclic  

Graph poisoning is blocked.

---

### RG-WEAK-FORMAT-005 — Field-Scoped Weak Validation

Applies **only** to explicitly allow-listed fields:

- URL fields  
- Module path fields  
- Package name fields  

Checks are:

- Regex-based  
- Protocol-agnostic  
- Syntactic only  

> Governance does **not** guarantee downstream usability of non-empty values unless explicitly validated here.

This limitation is declared, not hidden.

---

## Contradiction Rule (Minimal & Syntactic)

A contradiction is defined as:

> Two invariants asserting mutually exclusive values  
> on the same entity  
> using the same predicate key

- Predicate key = exact JSON key name  
- No cross-predicate reasoning  
- No semantic inference  

Semantic contradictions are deferred to **Validation / DFR**.

---

## Retry Model

### Retry Budget

- Exactly **1 retry**
- Applies only on `FAIL`
- `PASS` bypasses retry accounting

### Retry Protection (Invariant Locking)

- Each check declares which sections it validated  
- Sections with **zero failures** are locked  
- Sections involved in failures remain mutable  

This prevents regression without freezing bad baselines.

Retry is **surgical**, not blind.

---

## Error Reporting

- Maximum errors returned: `max_errors` (default: 5)
- Errors are structured:

```json
{
  "check_id": "RG-DAG-004",
  "section": "build_dag",
  "message": "Cycle detected involving node 'backend'",
  "reference": "backend"
}
```

Failure classification is informational only.
It does not alter retry rules or admissibility criteria.

Freeze Semantics
Preconditions

All must be true:

All enabled checks PASS

Governance hash recorded

PLAN_FROZEN ledger entry written atomically

Retry budget is irrelevant on PASS.

Guarantees

Plan becomes immutable

Execution authority granted

Resume eligibility enabled

Ledger Interaction (Limited)

Governance may read the Progress Ledger only to:

Determine retry count

Validate resume eligibility

Governance decisions are otherwise independent of ledger history.

This preserves replay determinism.

Known & Owned Failure Modes

Governance intentionally allows:

Vacuous but complete plans

Semantic contradictions across predicates

Structurally admissible but useless artifacts

These failures are deferred to:

Validation

Deterministic Failure Replay (DFR)

This is by design.

What Governance Refuses To Do

Semantic reasoning

Intent validation

Auto-fixing

Adaptive behavior

Planner trust

Execution safety guarantees

Project Structure
MA_3rd_layer/
├── src/
│   └── governance/
│       ├── __init__.py
│       ├── engine.py
│       ├── reviewer.py
│       ├── schema.py
│       ├── hashing.py
│       └── manifest.json
├── tests/
│   ├── valid_plan.json
│   ├── fail_schema_version.json
│   ├── fail_empty_invariant.json
│   ├── fail_reference_syntax.json
│   ├── fail_dag_cycle.json
│   ├── fail_weak_format.json
│   └── get_hash.py
├── run_governance.py
├── requirements.txt
└── README.md
Test Philosophy

Layer 3 is verified via failure proofs, not unit tests.

Safety is proven only when invalid input is rejected.

If fail_dag_cycle.json passes, the system is broken.

Exit Codes
Code	Meaning
0	ADMISSIBLE (Authority Granted)
1	REJECTED (Authority Denied)
Final Statement

Governance enforces admissibility, not usefulness; authority, not correctness.

A reviewer may disagree with the philosophy.
They cannot break the logic.

License

MIT License
© 2026 Nesar

