from benchmarks.cases import ADVERSARIAL_CASES
from benchmarks.runner import run_case

for case in ADVERSARIAL_CASES:
    r = run_case(case)
    print(f"{case.id}: passed={r.passed}, risk_tier={r.risk_tier}, detail={r.detail}")