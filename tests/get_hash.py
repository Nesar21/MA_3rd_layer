import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.governance.schema import get_schema_version_hash

print("="*40)
print("REQUIRED SCHEMA VERSION HASH")
print("="*40)
print(get_schema_version_hash())
print("="*40)