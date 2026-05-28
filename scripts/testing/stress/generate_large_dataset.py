#!/usr/bin/env python3
"""Generate /tmp/stress-test-data/large_50k.csv (50K rows × 20 cols).

Deterministic (random.seed(42)). Used by run_data_analysis_stress_v3.py
to verify the SSE pipeline + agentic path scale to large datasets.
File is ~6MB — too big to commit; regenerate locally.
"""
import csv
import os
import random

random.seed(42)
out = "/tmp/stress-test-data"
os.makedirs(out, exist_ok=True)

with open(f"{out}/large_50k.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([f"feature_{i}" for i in range(15)] + [f"cat_{j}" for j in range(4)] + ["target"])
    for _ in range(50_000):
        w.writerow(
            [round(random.gauss(0, 1 + i * 0.1), 4) for i in range(15)]
            + [random.choice(["A", "B", "C", "D", "E"]) for _ in range(4)]
            + [random.randint(0, 1)]
        )
print(f"wrote {out}/large_50k.csv ({os.path.getsize(out + '/large_50k.csv')} bytes)")
