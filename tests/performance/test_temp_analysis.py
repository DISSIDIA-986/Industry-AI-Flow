import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")

# ENmatplotlib
plt.rcParams["figure.figsize"] = (12, 8)
plt.rcParams["savefig.dpi"] = 150
plt.rcParams["figure.dpi"] = 100


def analyze_housing_data():
    """EN"""

    print("=== EN ===")

    # 1. EN
    data_path = "test_resources/datasets/Housing.csv"
    df = pd.read_csv(data_path)

    print(f"EN: {df.shape}")
    print(f"EN: {list(df.columns)}")

    # 2. EN
    print("\n=== EN ===")
    print(f"EN: {df['price'].min():,.0f} - {df['price'].max():,.0f}")
    print(f"EN: {df['price'].mean():,.0f}")
    print(f"EN: {df['area'].mean():,.0f} sq.ft")

    # 3. EN
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    correlation = df[numeric_cols].corr()["price"].sort_values(ascending=False)
    print("\n=== EN ===")
    for feature, corr in correlation.items():
        if feature != "price":
            print(f"{feature}: {corr:.3f}")

    # 4. EN
    results = {
        "total_records": len(df),
        "price_stats": {
            "min": float(df["price"].min()),
            "max": float(df["price"].max()),
            "mean": float(df["price"].mean()),
            "median": float(df["price"].median()),
        },
        "area_stats": {
            "min": float(df["area"].min()),
            "max": float(df["area"].max()),
            "mean": float(df["area"].mean()),
            "median": float(df["area"].median()),
        },
        "correlations": correlation.to_dict(),
        "feature_importance": correlation.abs()
        .sort_values(ascending=False)[1:]
        .to_dict(),
    }

    print("\n=== EN ===")
    print(f"EN {results['total_records']} EN")
    print(f"EN: {list(results['feature_importance'].keys())[:3]}")

    return results


# EN
if __name__ == "__main__":
    results = analyze_housing_data()
    print(f"\nEN: {len(results)} EN")
