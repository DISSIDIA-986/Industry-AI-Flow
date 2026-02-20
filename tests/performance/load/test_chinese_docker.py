#!/usr/bin/env python3
"""
DockerEN
"""

import os
import sys

sys.path.insert(0, "/app/utils")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

print("🚀 ENDockerEN")

# EN
try:
    import matplotlib_chinese_support

    success = matplotlib_chinese_support.setup_chinese_matplotlib()
    if success:
        print("✅ EN")
    else:
        print("⚠️ EN")
except Exception as e:
    print(f"⚠️ EN: {e}")
    # EN
    plt.rcParams["font.sans-serif"] = [
        "WenQuanYi Zen Hei",
        "WenQuanYi Micro Hei",
        "SimHei",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    print("✅ EN")

# EN
print("📊 EN...")
plt.figure(figsize=(10, 6))
x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.plot(x, y, label="EN", linewidth=2)
plt.title("DockerEN", fontsize=16, fontweight="bold")
plt.xlabel("XEN(EN)", fontsize=12)
plt.ylabel("YEN", fontsize=12)
plt.legend()
plt.grid(True, alpha=0.3)

# EN
output_path = "/workspace/output/dockerEN.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()

print(f"✅ DockerEN: {output_path}")

# EN
if os.path.exists(output_path):
    file_size = os.path.getsize(output_path)
    print(f"📁 EN: {file_size:,} bytes")
    print("🎉 DockerEN!")
else:
    print("❌ EN")
