#!/usr/bin/env python3
"""
EN
"""

import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# EN
sys.path.append(str(Path(__file__).parent))

# EN
try:
    from backend.utils.matplotlib_chinese_support import setup_chinese_matplotlib

    setup_chinese_matplotlib()
    print("✅ EN")
except ImportError:
    print("⚠️ EN,EN")

import matplotlib.pyplot as plt
import seaborn as sns


def test_chinese_visualization():
    """EN"""
    print("=" * 60)
    print("🇨🇳 EN")
    print("=" * 60)

    # EN
    data_path = "test_resources/datasets/Housing.csv"
    df = pd.read_csv(data_path)

    print(f"📊 EN: {df.shape}")

    # EN
    output_dir = Path("chinese_visualization_output")
    output_dir.mkdir(exist_ok=True)

    generated_charts = []

    # EN1: EN(EN)
    plt.figure(figsize=(15, 5))

    plt.subplot(1, 3, 1)
    plt.hist(df["price"], bins=30, alpha=0.7, color="skyblue", edgecolor="black")
    plt.title("EN", fontsize=14, fontweight="bold")
    plt.xlabel("EN(EN)", fontsize=12)
    plt.ylabel("EN", fontsize=12)

    plt.subplot(1, 3, 2)
    plt.boxplot(df["price"])
    plt.title("EN", fontsize=14, fontweight="bold")
    plt.ylabel("EN(EN)", fontsize=12)

    plt.subplot(1, 3, 3)
    # EN
    price_bins = [0, 3000000, 5000000, 7000000, 10000000, float("inf")]
    price_labels = ["EN", "EN", "EN", "EN", "EN"]
    df["price_category"] = pd.cut(
        df["price"], bins=price_bins, labels=price_labels, right=False
    )
    category_counts = df["price_category"].value_counts()

    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]
    plt.bar(
        category_counts.index, category_counts.values, color=colors, edgecolor="black"
    )
    plt.title("EN", fontsize=14, fontweight="bold")
    plt.xlabel("EN", fontsize=12)
    plt.ylabel("EN", fontsize=12)
    plt.xticks(rotation=15)

    plt.tight_layout()
    chart1 = output_dir / "EN_EN.png"
    plt.savefig(chart1, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart1)
    print("✅ EN(EN)")

    # EN2: EN
    plt.figure(figsize=(16, 10))

    # EN-EN
    plt.subplot(2, 3, 1)
    plt.scatter(df["area"], df["price"], alpha=0.6, color="coral", edgecolor="black")
    plt.xlabel("EN(EN)", fontsize=12)
    plt.ylabel("EN(EN)", fontsize=12)
    plt.title("EN-EN", fontsize=14, fontweight="bold")

    # EN
    plt.subplot(2, 3, 2)
    bedroom_avg = df.groupby("bedrooms")["price"].mean()
    bars = plt.bar(
        bedroom_avg.index, bedroom_avg.values, color="lightblue", edgecolor="black"
    )
    plt.xlabel("EN", fontsize=12)
    plt.ylabel("EN(EN)", fontsize=12)
    plt.title("EN", fontsize=14, fontweight="bold")
    # EN
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:,.0f}",
            ha="center",
            va="bottom",
        )

    # EN
    plt.subplot(2, 3, 3)
    furnish_avg = df.groupby("furnishingstatus")["price"].mean()
    furnish_labels = {"furnished": "EN", "semi-furnished": "EN", "unfurnished": "EN"}
    furnish_avg.index = furnish_avg.index.map(furnish_labels)
    colors_furnish = ["#FF6B6B", "#4ECDC4", "#45B7D1"]
    bars = plt.bar(
        furnish_avg.index, furnish_avg.values, color=colors_furnish, edgecolor="black"
    )
    plt.xlabel("EN", fontsize=12)
    plt.ylabel("EN(EN)", fontsize=12)
    plt.title("EN", fontsize=14, fontweight="bold")
    # EN
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:,.0f}",
            ha="center",
            va="bottom",
        )

    # EN
    plt.subplot(2, 3, 4)
    mainroad_avg = df.groupby("mainroad")["price"].mean()
    mainroad_labels = {"yes": "EN", "no": "EN"}
    mainroad_avg.index = mainroad_avg.index.map(mainroad_labels)
    colors_mainroad = ["#96CEB4", "#FFEAA7"]
    bars = plt.bar(
        mainroad_avg.index,
        mainroad_avg.values,
        color=colors_mainroad,
        edgecolor="black",
    )
    plt.xlabel("EN", fontsize=12)
    plt.ylabel("EN(EN)", fontsize=12)
    plt.title("EN", fontsize=14, fontweight="bold")
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:,.0f}",
            ha="center",
            va="bottom",
        )

    # EN
    plt.subplot(2, 3, 5)
    ac_avg = df.groupby("airconditioning")["price"].mean()
    ac_labels = {"yes": "EN", "no": "EN"}
    ac_avg.index = ac_avg.index.map(ac_labels)
    colors_ac = ["#FF6B6B", "#DDA0DD"]
    bars = plt.bar(ac_avg.index, ac_avg.values, color=colors_ac, edgecolor="black")
    plt.xlabel("EN", fontsize=12)
    plt.ylabel("EN(EN)", fontsize=12)
    plt.title("EN", fontsize=14, fontweight="bold")
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:,.0f}",
            ha="center",
            va="bottom",
        )

    # EN
    plt.subplot(2, 3, 6)
    parking_avg = df.groupby("parking")["price"].mean()
    bars = plt.bar(
        parking_avg.index, parking_avg.values, color="lightgreen", edgecolor="black"
    )
    plt.xlabel("EN", fontsize=12)
    plt.ylabel("EN(EN)", fontsize=12)
    plt.title("EN", fontsize=14, fontweight="bold")
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:,.0f}",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    chart2 = output_dir / "EN_EN.png"
    plt.savefig(chart2, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart2)
    print("✅ EN(EN)")

    # EN3: EN
    plt.figure(figsize=(12, 10))

    # EN
    feature_names = {
        "price": "EN",
        "area": "EN",
        "bedrooms": "EN",
        "bathrooms": "EN",
        "stories": "EN",
        "mainroad": "EN",
        "guestroom": "EN",
        "basement": "EN",
        "hotwaterheating": "EN",
        "airconditioning": "EN",
        "parking": "EN",
        "prefarea": "EN",
        "furnishingstatus": "EN",
    }

    # EN
    numeric_features = ["price", "area", "bedrooms", "bathrooms", "stories", "parking"]
    correlation_matrix = df[numeric_features].corr()

    # EN
    correlation_matrix.index = [
        feature_names.get(col, col) for col in correlation_matrix.index
    ]
    correlation_matrix.columns = [
        feature_names.get(col, col) for col in correlation_matrix.columns
    ]

    mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
    sns.heatmap(
        correlation_matrix,
        mask=mask,
        annot=True,
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
        fmt=".3f",
        annot_kws={"size": 10},
    )
    plt.title("EN", fontsize=16, fontweight="bold", pad=20)
    plt.tight_layout()

    chart3 = output_dir / "EN_EN.png"
    plt.savefig(chart3, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart3)
    print("✅ EN(EN)")

    # EN4: EN
    plt.figure(figsize=(20, 12))

    # EN:EN
    plt.subplot(2, 4, 1)
    plt.hist(df["price"], bins=20, alpha=0.7, color="lightcoral", edgecolor="black")
    plt.axvline(
        df["price"].mean(),
        color="red",
        linestyle="--",
        linewidth=2,
        label=f'EN: {df["price"].mean():,.0f}',
    )
    plt.xlabel("EN(EN)")
    plt.ylabel("EN")
    plt.title("EN", fontweight="bold")
    plt.legend()

    # EN:EN
    plt.subplot(2, 4, 2)
    plt.hist(df["area"], bins=20, alpha=0.7, color="lightblue", edgecolor="black")
    plt.axvline(
        df["area"].mean(),
        color="red",
        linestyle="--",
        linewidth=2,
        label=f'EN: {df["area"].mean():,.0f}',
    )
    plt.xlabel("EN(EN)")
    plt.ylabel("EN")
    plt.title("EN", fontweight="bold")
    plt.legend()

    # EN:EN
    plt.subplot(2, 4, 3)
    furnish_counts = df["furnishingstatus"].value_counts()
    furnish_labels_map = {
        "furnished": "EN",
        "semi-furnished": "EN",
        "unfurnished": "EN",
    }
    labels = [furnish_labels_map.get(x, x) for x in furnish_counts.index]
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1"]
    explode = (0.05, 0.05, 0.05)
    plt.pie(
        furnish_counts.values,
        labels=labels,
        autopct="%1.1f%%",
        colors=colors,
        explode=explode,
    )
    plt.title("EN", fontweight="bold")

    # EN2:EN
    plt.subplot(2, 4, 4)
    mainroad_counts = df["mainroad"].value_counts()
    mainroad_labels_map = {"yes": "EN", "no": "EN"}
    labels = [mainroad_labels_map.get(x, x) for x in mainroad_counts.index]
    colors = ["#96CEB4", "#FFEAA7"]
    plt.pie(mainroad_counts.values, labels=labels, autopct="%1.1f%%", colors=colors)
    plt.title("EN", fontweight="bold")

    # EN:EN
    plt.subplot(2, 4, 5)
    # EN
    df.boxplot(column="price", by="furnishingstatus", ax=plt.gca())
    plt.xlabel("EN")
    plt.ylabel("EN(EN)")
    plt.title("EN", fontweight="bold")
    plt.xticks([1, 2, 3], ["EN", "EN", "EN"])

    # EN2:ENvsEN
    plt.subplot(2, 4, 6)
    bedroom_data = [
        df[df["bedrooms"] == i]["price"].values for i in sorted(df["bedrooms"].unique())
    ]
    plt.boxplot(bedroom_data)
    plt.xlabel("EN")
    plt.ylabel("EN(EN)")
    plt.title("EN", fontweight="bold")
    plt.grid(True, alpha=0.3)

    # EN:EN
    plt.subplot(2, 4, 7)
    stats_text = f"""EN:

EN: {len(df):,} EN

EN:
• EN: {df['price'].mean():,.0f} EN
• EN: {df['price'].median():,.0f} EN
• EN: {df['price'].std():,.0f} EN
• EN: {df['price'].min():,.0f} EN
• EN: {df['price'].max():,.0f} EN

EN:
• EN: {df['area'].mean():,.0f} EN
• EN: {df['area'].median():,.0f} EN
• EN: {df['area'].min():,} - {df['area'].max():,} EN
"""
    plt.text(
        0.05,
        0.95,
        stats_text,
        transform=plt.gca().transAxes,
        fontsize=10,
        verticalalignment="top",
        fontfamily="monospace",
    )
    plt.axis("off")
    plt.title("EN", fontweight="bold")

    # EN2:EN
    plt.subplot(2, 4, 8)
    insights_text = f"""EN:

🏠 EN:
• EN: {len(df[df['price'] < 3000000]):,} EN
• EN: {len(df[(df['price'] >= 3000000) & (df['price'] < 5000000)]):,} EN
• EN: {len(df[(df['price'] >= 5000000) & (df['price'] < 7000000)]):,} EN
• EN: {len(df[(df['price'] >= 7000000) & (df['price'] < 10000000)]):,} EN
• EN: {len(df[df['price'] >= 10000000]):,} EN

🔑 EN:
• EN: {df[['area', 'price']].corr().iloc[0,1]:.3f}
• EN: {df[df['mainroad'] == 'yes'].shape[0]/len(df)*100:.1f}%
• EN: {df[df['furnishingstatus'] == 'furnished'].shape[0]/len(df)*100:.1f}%
• EN: {df[df['airconditioning'] == 'yes'].shape[0]/len(df)*100:.1f}%
"""
    plt.text(
        0.05,
        0.95,
        insights_text,
        transform=plt.gca().transAxes,
        fontsize=9,
        verticalalignment="top",
    )
    plt.axis("off")
    plt.title("EN", fontweight="bold")

    plt.tight_layout()
    chart4 = output_dir / "EN_EN.png"
    plt.savefig(chart4, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart4)
    print("✅ EN(EN)")

    return generated_charts, output_dir


def test_chinese_text_rendering():
    """EN"""
    print("\n" + "=" * 60)
    print("📝 EN")
    print("=" * 60)

    plt.figure(figsize=(12, 8))

    # EN
    plt.subplot(2, 2, 1)
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)

    plt.plot(x, y1, label="EN", linewidth=2, color="blue")
    plt.plot(x, y2, label="EN", linewidth=2, color="red")
    plt.title("EN", fontsize=14, fontweight="bold")
    plt.xlabel("XEN(EN)")
    plt.ylabel("YEN")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(2, 2, 2)
    categories = ["EN", "EN", "EN", "EN", "EN"]
    values = [25, 30, 20, 15, 10]
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]

    bars = plt.bar(categories, values, color=colors, edgecolor="black")
    plt.title("EN", fontsize=14, fontweight="bold")
    plt.xlabel("EN")
    plt.ylabel("EN(%)")

    # EN
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height}%",
            ha="center",
            va="bottom",
        )

    plt.subplot(2, 2, 3)
    # EN
    sizes = [35, 25, 20, 15, 5]
    labels = ["EN", "EN", "EN", "EN", "EN"]
    explode = (0.05, 0.05, 0.05, 0.05, 0.1)
    colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))

    plt.pie(sizes, explode=explode, labels=labels, autopct="%1.1f%%", colors=colors)
    plt.title("EN", fontsize=14, fontweight="bold")

    plt.subplot(2, 2, 4)
    # EN
    plt.text(
        0.5,
        0.8,
        "EN",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        transform=plt.gca().transAxes,
    )
    plt.text(
        0.5,
        0.6,
        "EN!",
        ha="center",
        va="center",
        fontsize=14,
        color="red",
        transform=plt.gca().transAxes,
    )
    plt.text(
        0.5,
        0.4,
        "EN:,.!?",
        ha="center",
        va="center",
        fontsize=12,
        color="blue",
        transform=plt.gca().transAxes,
    )
    plt.text(
        0.5,
        0.2,
        "EN:123.45EN",
        ha="center",
        va="center",
        fontsize=12,
        color="green",
        transform=plt.gca().transAxes,
    )

    plt.title("EN", fontsize=14, fontweight="bold")
    plt.axis("off")

    plt.tight_layout()

    # EN
    output_dir = Path("chinese_visualization_output")
    output_dir.mkdir(exist_ok=True)

    chart_path = output_dir / "EN.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()

    print("✅ EN")
    return chart_path


def main():
    """EN"""
    print("🚀 EN")
    print("🎯 ENmatplotlibEN")

    try:
        # EN1: EN
        charts, output_dir = test_chinese_visualization()
        print(f"\n📊 EN")
        print(f"   EN: {len(charts)}")
        print(f"   EN: {output_dir}")

        # EN2: EN
        text_chart = test_chinese_text_rendering()
        print(f"   EN: {text_chart}")

        # EN
        print(f"\n📁 EN:")
        all_files = list(output_dir.glob("*.png"))
        for i, file in enumerate(all_files, 1):
            file_size = file.stat().st_size
            print(f"   {i}. {file.name} ({file_size:,} bytes)")

        print(f"\n🎉 EN!")
        print("✅ EN,EN,EN")
        print("✅ EN,EN")
        print("✅ EN")

        return True

    except Exception as e:
        print(f"❌ EN: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
