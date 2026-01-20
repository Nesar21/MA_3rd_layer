import json
import os
import sys
from src.governance.engine import GovernanceEngine
from src.governance.schema import get_schema_version_hash

def main():
    """
    CLI Entry Point for Layer 3.
    Usage: python run_governance.py [path_to_plan.json]
    """
    
    # 1. Setup Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_path = os.path.join(base_dir, 'src', 'governance', 'manifest.json')
    
    # 2. Initialize Engine
    try:
        engine = GovernanceEngine(manifest_path)
        print(f"[*] Governance Engine Initialized.")
        print(f"[*] Governance Version: {engine.governance_version}")
        print(f"[*] Expected Schema Version: {get_schema_version_hash()}")
    except Exception as e:
        print(f"[!] FATAL: Engine Initialization Failed: {e}")
        sys.exit(1)

    # 3. Load Input Plan
    # If no file provided, we use a dummy path or fail
    if len(sys.argv) < 2:
        print("\n[Usage] python run_governance.py <plan.json>")
        print("No plan provided. Exiting.")
        sys.exit(0)
    
    plan_path = sys.argv[1]
    print(f"[*] Loading Plan: {plan_path}")

    try:
        with open(plan_path, 'r') as f:
            plan = json.load(f)
    except Exception as e:
        print(f"[!] FATAL: Could not load plan JSON: {e}")
        sys.exit(1)

    # 4. Execute Evaluation
    print("[*] Evaluating...")
    result_event = engine.evaluate_plan(plan)

    # 5. Output Result
    print("\n" + "="*40)
    print("GOVERNANCE VERDICT")
    print("="*40)
    print(json.dumps(result_event, indent=2))
    
    if result_event["authority_granted"]:
        sys.exit(0) # Success
    else:
        sys.exit(1) # Failure (as intended)

if __name__ == "__main__":
    main()