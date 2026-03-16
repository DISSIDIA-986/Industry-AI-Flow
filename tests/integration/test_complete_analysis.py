#!/usr/bin/env python3
"""
EN RAG EN
EN
"""

import os
import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")

# ENmatplotlib
plt.style.use("default")
plt.rcParams["figure.figsize"] = (12, 8)
plt.rcParams["savefig.dpi"] = 150
plt.rcParams["figure.dpi"] = 100


def test_complete_analysis():
    """EN"""
    print("🚀 EN")
    print("=" * 60)

    # 1. EN
    print("📊 1. EN")
    data_path = "test_resources/datasets/Housing.csv"
    df = pd.read_csv(data_path)
    print(f"   ✅ EN: {df.shape}")

    # 2. EN
    print("\n🔬 2. EN")

    # EN
    numeric_stats = df.describe()
    print(f"   ✅ EN: {len(numeric_stats.columns)} EN")

    # EN
    missing_values = df.isnull().sum()
    total_missing = missing_values.sum()
    print(f"   ✅ EN: {total_missing} EN")

    # 3. EN
    print("\n⚙️ 3. EN")

    # EN
    categorical_cols = df.select_dtypes(include=["object"]).columns
    print(f"   EN: {list(categorical_cols)}")

    df_processed = df.copy()
    le = LabelEncoder()

    for col in categorical_cols:
        df_processed[col] = le.fit_transform(df_processed[col])

    print(f"   ✅ EN")

    # 4. EN
    print("\n🤖 4. EN")

    X = df_processed.drop("price", axis=1)
    y = df_processed["price"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"   EN: {X_train.shape}, EN: {X_test.shape}")

    # EN
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)

    # EN
    y_pred = rf_model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)

    print(f"   ✅ EN:")
    print(f"      MAE: {mae:,.0f}")
    print(f"      RMSE: {rmse:,.0f}")
    print(f"      R²: {r2:.3f}")

    # 5. EN
    print("\n📊 5. EN")

    feature_importance = pd.DataFrame(
        {"feature": X.columns, "importance": rf_model.feature_importances_}
    ).sort_values("importance", ascending=False)

    print("   EN5EN:")
    for i, (_, row) in enumerate(feature_importance.head().iterrows(), 1):
        print(f"   {i}. {row['feature']}: {row['importance']:.3f}")

    # 6. EN
    print("\n📈 6. EN")

    # EN
    output_dir = Path("complete_analysis_output")
    output_dir.mkdir(exist_ok=True)

    generated_charts = []

    # EN1: EN
    plt.figure(figsize=(15, 5))

    plt.subplot(1, 3, 1)
    plt.hist(df["price"], bins=30, alpha=0.7, color="skyblue", edgecolor="black")
    plt.title("EN")
    plt.xlabel("EN")
    plt.ylabel("EN")

    plt.subplot(1, 3, 2)
    plt.boxplot(df["price"])
    plt.title("EN")
    plt.ylabel("EN")

    plt.subplot(1, 3, 3)
    plt.hist(
        np.log1p(df["price"]), bins=30, alpha=0.7, color="lightgreen", edgecolor="black"
    )
    plt.title("EN")
    plt.xlabel("log(EN)")
    plt.ylabel("EN")

    plt.tight_layout()
    chart1 = output_dir / "price_distribution_analysis.png"
    plt.savefig(chart1, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart1)
    print("   ✅ EN")

    # EN2: EN-EN
    plt.figure(figsize=(15, 5))

    plt.subplot(1, 3, 1)
    plt.scatter(df["area"], df["price"], alpha=0.6, color="coral")
    plt.xlabel("EN")
    plt.ylabel("EN")
    plt.title("EN-EN")

    plt.subplot(1, 3, 2)
    bedroom_groups = df.groupby("bedrooms")["price"].mean()
    plt.bar(
        bedroom_groups.index,
        bedroom_groups.values,
        color="lightblue",
        edgecolor="black",
    )
    plt.xlabel("EN")
    plt.ylabel("EN")
    plt.title("EN-EN")

    plt.subplot(1, 3, 3)
    furnish_groups = df.groupby("furnishingstatus")["price"].mean()
    colors = ["gold", "lightgreen", "lightcoral"]
    plt.bar(
        range(len(furnish_groups)),
        furnish_groups.values,
        color=colors,
        edgecolor="black",
    )
    plt.xticks(range(len(furnish_groups)), furnish_groups.index, rotation=45)
    plt.ylabel("EN")
    plt.title("EN-EN")

    plt.tight_layout()
    chart2 = output_dir / "feature_price_analysis.png"
    plt.savefig(chart2, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart2)
    print("   ✅ EN-EN")

    # EN3: EN
    plt.figure(figsize=(12, 8))
    numeric_df = df.select_dtypes(include=[np.number])
    correlation_matrix = numeric_df.corr()

    mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
    sns.heatmap(
        correlation_matrix,
        mask=mask,
        annot=True,
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
        fmt=".2f",
    )
    plt.title("EN")
    plt.tight_layout()

    chart3 = output_dir / "correlation_heatmap.png"
    plt.savefig(chart3, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart3)
    print("   ✅ EN")

    # EN4: EN
    plt.figure(figsize=(15, 5))

    plt.subplot(1, 3, 1)
    plt.scatter(y_test, y_pred, alpha=0.6, color="purple", edgecolor="black")
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], "r--", lw=2)
    plt.xlabel("EN")
    plt.ylabel("EN")
    plt.title("ENvsEN")

    plt.subplot(1, 3, 2)
    residuals = y_test - y_pred
    plt.scatter(y_pred, residuals, alpha=0.6, color="orange")
    plt.axhline(y=0, color="r", linestyle="--")
    plt.xlabel("EN")
    plt.ylabel("EN")
    plt.title("EN")

    plt.subplot(1, 3, 3)
    plt.hist(residuals, bins=30, alpha=0.7, color="lightgreen", edgecolor="black")
    plt.xlabel("EN")
    plt.ylabel("EN")
    plt.title("EN")

    plt.tight_layout()
    chart4 = output_dir / "model_prediction_analysis.png"
    plt.savefig(chart4, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart4)
    print("   ✅ EN")

    # EN5: EN
    plt.figure(figsize=(12, 8))
    top_features = feature_importance.head(10)
    colors = plt.cm.Set3(np.linspace(0, 1, len(top_features)))

    plt.barh(
        range(len(top_features)),
        top_features["importance"],
        color=colors,
        edgecolor="black",
    )
    plt.yticks(range(len(top_features)), top_features["feature"])
    plt.xlabel("EN")
    plt.title("EN (Top 10)")
    plt.gca().invert_yaxis()

    # EN
    for i, v in enumerate(top_features["importance"]):
        plt.text(v + 0.01, i, f"{v:.3f}", va="center")

    plt.tight_layout()
    chart5 = output_dir / "feature_importance.png"
    plt.savefig(chart5, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart5)
    print("   ✅ EN")

    # 7. EN
    print("\n📋 7. EN")

    report = {
        "dataset_info": {
            "shape": df.shape,
            "features": list(df.columns),
            "numeric_features": list(df.select_dtypes(include=[np.number]).columns),
            "categorical_features": list(df.select_dtypes(include=["object"]).columns),
            "missing_values": int(total_missing),
        },
        "statistical_summary": {
            "price_stats": {
                "mean": float(df["price"].mean()),
                "median": float(df["price"].median()),
                "std": float(df["price"].std()),
                "min": float(df["price"].min()),
                "max": float(df["price"].max()),
            },
            "area_stats": {
                "mean": float(df["area"].mean()),
                "median": float(df["area"].median()),
                "std": float(df["area"].std()),
                "min": float(df["area"].min()),
                "max": float(df["area"].max()),
            },
        },
        "model_performance": {
            "mae": float(mae),
            "mse": float(mse),
            "rmse": float(rmse),
            "r2_score": float(r2),
        },
        "feature_importance": feature_importance.set_index("feature")["importance"]
        .head(10)
        .to_dict(),
        "key_insights": [
            f"EN {df.shape[0]} EN {df.shape[1]} EN",
            f"EN: {df['price'].min():,.0f} - {df['price'].max():,.0f}",
            f"EN: {correlation_matrix.loc['area', 'price']:.3f}",
            f"ENR²EN: {r2:.3f}",
            f"EN: {feature_importance.iloc[0]['feature']}",
        ],
    }

    # EN
    import json

    report_file = output_dir / "analysis_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("   ✅ EN")

    # 8. EN
    print("\n" + "=" * 60)
    print("🎉 EN!")
    print("=" * 60)

    print(f"📊 EN:")
    print(f"   EN: {report['dataset_info']['shape']}")
    print(f"   EN: {report['statistical_summary']['price_stats']['mean']:,.0f}")
    print(f"   EN-EN: {correlation_matrix.loc['area', 'price']:.3f}")

    print(f"\n🤖 EN:")
    print(f"   R² EN: {r2:.3f}")
    print(f"   EN: {mae:,.0f}")
    print(f"   EN: {feature_importance.iloc[0]['feature']}")

    print(f"\n📈 EN: {len(generated_charts)} EN")
    for i, chart in enumerate(generated_charts, 1):
        print(f"   {i}. {chart.name}")

    print(f"\n📁 EN: {output_dir.absolute()}")

    return {
        "success": True,
        "data_stats": report["dataset_info"],
        "model_performance": report["model_performance"],
        "generated_charts": len(generated_charts),
        "output_dir": str(output_dir.absolute()),
    }


def test_code_generation_simulation():
    """ENLLMEN"""
    print("\n" + "=" * 60)
    print("🤖 EN")
    print("=" * 60)

    # EN
    generated_code = '''
def generate_advanced_insights(df):
    """EN"""

    insights = []

    # 1. EN
    price_quartiles = df['price'].quantile([0.25, 0.5, 0.75])
    affordable = df[df['price'] <= price_quartiles[0.25]]
    luxury = df[df['price'] >= price_quartiles[0.75]]

    insights.append(f"EN(EN25%): EN {affordable['price'].mean():,.0f}")
    insights.append(f"EN(EN25%): EN {luxury['price'].mean():,.0f}")

    # 2. EN
    df['price_per_sqft'] = df['price'] / df['area']
    best_value = df.nsmallest(5, 'price_per_sqft')

    insights.append(f"EN: EN {best_value['price_per_sqft'].mean():.0f}")

    # 3. EN
    mainroad_premium = df[df['mainroad'] == 'yes']['price'].mean() / df[df['mainroad'] == 'no']['price'].mean()
    insights.append(f"EN: {mainroad_premium:.1%}")

    # 4. EN
    furnished_premium = df[df['furnishingstatus'] == 'furnished']['price'].mean() / df[df['furnishingstatus'] == 'unfurnished']['price'].mean()
    insights.append(f"EN: {furnished_premium:.1%}")

    return insights
'''

    try:
        # EN
        df = pd.read_csv("test_resources/datasets/Housing.csv")

        # EN
        exec_locals = {}
        exec(generated_code, {"df": df, "pd": pd}, exec_locals)

        insights_func = exec_locals["generate_advanced_insights"]
        insights = insights_func(df)

        print("✅ EN!")
        print("📊 EN:")
        for i, insight in enumerate(insights, 1):
            print(f"   {i}. {insight}")

        return True, insights

    except Exception as e:
        print(f"❌ EN: {e}")
        return False, []


def main():
    """EN"""
    print("🚀 EN RAG EN")
    print("🎯 EN: ENEDA,EN,EN")

    # EN1: EN
    result1 = test_complete_analysis()

    # EN2: EN
    code_success, insights = test_code_generation_simulation()

    # EN
    print("\n" + "=" * 60)
    print("📊 EN")
    print("=" * 60)

    tests = [("EN", result1["success"]), ("EN", code_success)]

    all_success = True
    for test_name, success in tests:
        status = "✅ EN" if success else "❌ EN"
        print(f"   {test_name}: {status}")
        if not success:
            all_success = False

    if all_success:
        print("\n🎉 EN!")
        print("📈 RAG EN")

        print("\n🔧 EN:")
        print("✅ EN")
        print("✅ EN (EDA)")
        print("✅ EN")
        print("✅ EN (EN)")
        print("✅ EN")
        print("✅ EN")
        print("✅ EN")
        print("✅ EN")
        print("✅ EN")

        print("\n🎯 EN:")
        print(f"📊 EN {result1['data_stats']['shape']} EN")
        print(f"🤖 ENR²EN: {result1['model_performance']['r2_score']:.3f}")
        print(f"📈 EN {result1['generated_charts']} EN")
        print(f"💡 EN {len(insights)} EN")

        print("\n🚀 EN!")
        print("EN:")
        print("1. EN Docker EN")
        print("2. EN LangChain 1.0 EN")
        print("3. EN")
        print("4. EN")

    else:
        print("\n⚠️ EN")
        print("🔧 EN")

    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
