#!/usr/bin/env python3
"""
EN Docker EN
"""

import os
import sys
from pathlib import Path

import pandas as pd

# EN
sys.path.append(str(Path(__file__).parent))
REPO_ROOT = Path(__file__).resolve().parents[3]
HOUSING_DATASET_PATH = str(REPO_ROOT / "test_resources/datasets/Housing.csv")


def test_docker_connectivity():
    """ENDockerEN"""
    print("=" * 60)
    print("🐳 EN Docker EN")
    print("=" * 60)

    try:
        import docker

        client = docker.from_env()

        # ENDockerEN
        client.ping()
        print("✅ Docker EN!")

        # EN
        images = client.images.list()
        print(f"📦 EN {len(images)} EN Docker EN")

        # EN
        analysis_images = [
            img
            for img in images
            if any(tag.endswith("code-analysis") for tag in img.tags)
        ]

        if analysis_images:
            print("✅ EN:")
            for img in analysis_images:
                print(f"   {', '.join(img.tags)}")
            return True, client
        else:
            print("⚠️ EN,EN")
            return False, client

    except Exception as e:
        print(f"❌ Docker EN: {e}")
        return False, None


def test_code_execution_without_docker():
    """ENDockerEN"""
    print("\n" + "=" * 60)
    print("⚙️ EN Python EN(EN)")
    print("=" * 60)

    # EN Housing EN
    test_code = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ENmatplotlib
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['savefig.dpi'] = 150
plt.rcParams['figure.dpi'] = 100

def analyze_housing_data():
    """EN"""

    print("=== EN ===")

    # 1. EN
    data_path = "__HOUSING_DATASET_PATH__"
    df = pd.read_csv(data_path)

    print(f"EN: {df.shape}")
    print(f"EN: {list(df.columns)}")

    # 2. EN
    print("\\n=== EN ===")
    print(f"EN: {df['price'].min():,.0f} - {df['price'].max():,.0f}")
    print(f"EN: {df['price'].mean():,.0f}")
    print(f"EN: {df['area'].mean():,.0f} sq.ft")

    # 3. EN
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    correlation = df[numeric_cols].corr()['price'].sort_values(ascending=False)
    print("\\n=== EN ===")
    for feature, corr in correlation.items():
        if feature != 'price':
            print(f"{feature}: {corr:.3f}")

    # 4. EN
    results = {
        "total_records": len(df),
        "price_stats": {
            "min": float(df['price'].min()),
            "max": float(df['price'].max()),
            "mean": float(df['price'].mean()),
            "median": float(df['price'].median())
        },
        "area_stats": {
            "min": float(df['area'].min()),
            "max": float(df['area'].max()),
            "mean": float(df['area'].mean()),
            "median": float(df['area'].median())
        },
        "correlations": correlation.to_dict(),
        "feature_importance": correlation.abs().sort_values(ascending=False)[1:].to_dict()
    }

    print("\\n=== EN ===")
    print(f"EN {results['total_records']} EN")
    print(f"EN: {list(results['feature_importance'].keys())[:3]}")

    return results

# EN
if __name__ == "__main__":
    results = analyze_housing_data()
    print(f"\\nEN: {len(results)} EN")
'''.replace("__HOUSING_DATASET_PATH__", HOUSING_DATASET_PATH)

    try:
        # EN
        script_path = Path("temp_analysis_script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(test_code)

        # EN
        output_dir = Path("temp/reports/docker_test_output")
        output_dir.mkdir(exist_ok=True)

        # EN
        modified_code = (
            test_code
            + """
import json

# EN
output_file = Path("temp/reports/docker_test_output/analysis_results.json")
results = analyze_housing_data()

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\\nEN: {output_file}")
"""
        )

        # EN
        exec_globals = {}
        exec(modified_code, exec_globals)

        print("✅ EN!")

        # EN
        result_file = Path("temp/reports/docker_test_output/analysis_results.json")
        if result_file.exists():
            import json

            with open(result_file, "r", encoding="utf-8") as f:
                results = json.load(f)

            print("📊 EN:")
            print(f"   EN: {results['total_records']}")
            print(f"   EN: {results['price_stats']['mean']:,.0f}")
            print(
                f"   EN: {results['price_stats']['min']:,.0f} - {results['price_stats']['max']:,.0f}"
            )

            # EN
            print("   EN:")
            for i, (feature, importance) in enumerate(
                list(results["feature_importance"].items())[:5], 1
            ):
                print(f"   {i}. {feature}: {importance:.3f}")

            return True, results
        else:
            print("⚠️ EN")
            return False, None

    except Exception as e:
        print(f"❌ EN: {e}")
        import traceback

        traceback.print_exc()
        return False, None


def test_advanced_analysis():
    """EN"""
    print("\n" + "=" * 60)
    print("🧠 EN")
    print("=" * 60)

    advanced_code = '''
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

def advanced_housing_analysis():
    """EN - EN"""

    print("=== EN ===")

    # 1. EN
    data_path = "__HOUSING_DATASET_PATH__"
    df = pd.read_csv(data_path)

    print(f"EN: {df.shape}")

    # 2. EN
    # EN
    categorical_cols = ['mainroad', 'guestroom', 'basement',
                       'hotwaterheating', 'airconditioning', 'prefarea', 'furnishingstatus']

    le = LabelEncoder()
    for col in categorical_cols:
        df[col] = le.fit_transform(df[col])

    print(f"EN,EN: {df.shape}")

    # 3. EN
    X = df.drop('price', axis=1)
    y = df['price']

    # 4. EN
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"EN: {X_train.shape}")
    print(f"EN: {X_test.shape}")

    # 5. EN
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # 6. EN
    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)

    # 7. EN
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\\n=== EN ===")
    print(f"EN (MAE): {mae:,.0f}")
    print(f"EN (RMSE): {rmse:,.0f}")
    print(f"R² EN: {r2:.3f}")

    print("\\n=== EN ===")
    print(feature_importance.head(10))

    # 8. EN
    results = {
        "model_performance": {
            "mae": float(mae),
            "mse": float(mse),
            "rmse": float(rmse),
            "r2_score": float(r2)
        },
        "feature_importance": feature_importance.set_index('feature')['importance'].to_dict(),
        "data_shape": {
            "original": df.shape,
            "features": X.shape,
            "train_size": len(X_train),
            "test_size": len(X_test)
        }
    }

    print("\\n=== EN ===")
    print(f"ENR²EN: {r2:.3f}")
    print(f"EN: {feature_importance.iloc[0]['feature']}")

    return results

# EN
if __name__ == "__main__":
    results = advanced_housing_analysis()
    print(f"\\nEN,EN {len(results)} EN")
'''.replace("__HOUSING_DATASET_PATH__", HOUSING_DATASET_PATH)

    try:
        # EN
        script_path = Path("advanced_analysis_script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(advanced_code)

        # EN
        exec_globals = {}
        exec(advanced_code, exec_globals)

        print("✅ EN!")
        return True, exec_globals.get("results", {})

    except ImportError as e:
        if "sklearn" in str(e):
            print("⚠️ scikit-learn EN,EN")
            return None, None
        else:
            print(f"❌ EN: {e}")
            return False, None
    except Exception as e:
        print(f"❌ EN: {e}")
        return False, None


def test_visualization_generation():
    """EN"""
    print("\n" + "=" * 60)
    print("📊 EN")
    print("=" * 60)

    visualization_code = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def generate_visualizations():
    """EN"""

    print("=== EN ===")

    # EN
    output_dir = Path("temp/reports/docker_test_output/visualizations")
    output_dir.mkdir(parents=True, exist_ok=True)

    # EN
    data_path = "__HOUSING_DATASET_PATH__"
    df = pd.read_csv(data_path)

    plt.style.use('default')
    plt.rcParams['figure.figsize'] = (12, 8)

    generated_charts = []

    # 1. EN(EN + EN)
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.hist(df['price'], bins=30, alpha=0.7, color='skyblue', edgecolor='black')
    plt.title('EN')
    plt.xlabel('EN')
    plt.ylabel('EN')

    plt.subplot(1, 2, 2)
    plt.hist(df['price'], bins=30, alpha=0.3, density=True, color='skyblue')
    df['price'].plot(kind='kde', color='red', linewidth=2)
    plt.title('EN')
    plt.xlabel('EN')
    plt.ylabel('EN')

    plt.tight_layout()
    chart1_path = output_dir / "price_distribution_analysis.png"
    plt.savefig(chart1_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    generated_charts.append(str(chart1_path))
    print("✅ 1. EN")

    # 2. EN-EN(EN)
    plt.figure(figsize=(10, 6))
    colors = {'furnished': 'gold', 'semi-furnished': 'lightblue', 'unfurnished': 'lightgreen'}

    for furnish_status in df['furnishingstatus'].unique():
        subset = df[df['furnishingstatus'] == furnish_status]
        plt.scatter(subset['area'], subset['price'],
                   alpha=0.6, c=colors.get(furnish_status, 'gray'),
                   label=furnish_status, edgecolors='black', linewidth=0.5)

    plt.xlabel('EN (sq.ft)')
    plt.ylabel('EN')
    plt.title('EN-EN(EN)')
    plt.legend()
    plt.grid(True, alpha=0.3)

    chart2_path = output_dir / "area_price_by_furnishing.png"
    plt.savefig(chart2_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    generated_charts.append(str(chart2_path))
    print("✅ 2. EN-EN")

    # 3. EN
    plt.figure(figsize=(12, 8))
    numeric_df = df.select_dtypes(include=[np.number])
    correlation_matrix = numeric_df.corr()

    mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
    sns.heatmap(correlation_matrix, mask=mask, annot=True, cmap='coolwarm',
                center=0, square=True, linewidths=0.5, fmt='.2f')
    plt.title('EN')
    plt.tight_layout()

    chart3_path = output_dir / "correlation_heatmap_enhanced.png"
    plt.savefig(chart3_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    generated_charts.append(str(chart3_path))
    print("✅ 3. EN")

    # 4. EN(EN)
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('EN', fontsize=16)

    categorical_features = ['mainroad', 'guestroom', 'basement', 'hotwaterheating', 'airconditioning', 'prefarea']
    colors_list = ['lightcoral', 'lightgreen', 'lightskyblue', 'gold', 'lightpink', 'lightgray']

    for i, (feature, color) in enumerate(zip(categorical_features, colors_list)):
        row, col = i // 3, i % 3
        value_counts = df[feature].value_counts()

        axes[row, col].bar(value_counts.index, value_counts.values,
                          color=color, alpha=0.8, edgecolor='black')
        axes[row, col].set_title(f'{feature} EN')
        axes[row, col].set_ylabel('EN')

        # EN
        for j, v in enumerate(value_counts.values):
            axes[row, col].text(j, v + max(value_counts) * 0.01, str(v),
                               ha='center', fontweight='bold')

    plt.tight_layout()
    chart4_path = output_dir / "categorical_features_analysis.png"
    plt.savefig(chart4_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    generated_charts.append(str(chart4_path))
    print("✅ 4. EN")

    # 5. EN(EN)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('EN', fontsize=16)

    # EN
    df.boxplot(column='price', by='bedrooms', ax=axes[0,0])
    axes[0,0].set_title('EN')
    axes[0,0].set_xlabel('EN')

    # EN
    df.boxplot(column='price', by='furnishingstatus', ax=axes[0,1])
    axes[0,1].set_title('EN')
    axes[0,1].set_xlabel('EN')

    # EN
    df.boxplot(column='price', by='mainroad', ax=axes[1,0])
    axes[1,0].set_title('EN')
    axes[1,0].set_xlabel('EN')

    # EN
    df.boxplot(column='price', by='airconditioning', ax=axes[1,1])
    axes[1,1].set_title('EN')
    axes[1,1].set_xlabel('EN')

    plt.tight_layout()
    chart5_path = output_dir / "price_boxplot_analysis.png"
    plt.savefig(chart5_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    generated_charts.append(str(chart5_path))
    print("✅ 5. EN")

    print(f"\\n=== EN ===")
    print(f"EN {len(generated_charts)} EN")
    print(f"EN: {output_dir}")

    return generated_charts, output_dir

# EN
if __name__ == "__main__":
    charts, output_dir = generate_visualizations()
    print(f"\\nEN,EN {len(charts)} EN")
'''.replace("__HOUSING_DATASET_PATH__", HOUSING_DATASET_PATH)

    try:
        # EN
        exec_globals = {}
        exec(visualization_code, exec_globals)

        if exec_globals.get("charts"):
            charts = exec_globals["charts"]
            output_dir = exec_globals.get("output_dir")

            print("📊 EN:")
            for i, chart_path in enumerate(charts, 1):
                chart_name = Path(chart_path).name
                print(f"   {i}. {chart_name}")

            print(f"\\n📁 EN: {output_dir}")
            return True, charts
        else:
            print("⚠️ EN")
            return False, []

    except Exception as e:
        print(f"❌ EN: {e}")
        import traceback

        traceback.print_exc()
        return False, []


def main():
    """EN"""
    print("🚀 EN Docker EN")
    print("🎯 EN RAG EN")

    # EN1: DockerEN
    docker_available, client = test_docker_connectivity()

    # EN2: EN(EN)
    print("\n" + "=" * 60)
    print("EN 2/4: EN")
    print("=" * 60)
    code_success, basic_results = test_code_execution_without_docker()

    # EN3: EN
    print("\n" + "=" * 60)
    print("EN 3/4: EN")
    print("=" * 60)
    advanced_success, advanced_results = test_advanced_analysis()

    # EN4: EN
    print("\n" + "=" * 60)
    print("EN 4/4: EN")
    print("=" * 60)
    viz_success, charts = test_visualization_generation()

    # EN
    print("\n" + "=" * 60)
    print("📊 EN")
    print("=" * 60)

    tests = [
        ("DockerEN", docker_available),
        ("EN", code_success),
        ("EN", advanced_success if advanced_success is not None else False),
        ("EN", viz_success),
    ]

    success_count = 0
    for test_name, success in tests:
        if success is not None:
            status = "✅ EN" if success else "❌ EN"
            print(f"   {test_name}: {status}")
            if success:
                success_count += 1
        else:
            print(f"   {test_name}: ⚠️ EN")

    overall_success = success_count >= 3  # EN3EN

    if overall_success:
        print(f"\n🎉 EN! ({success_count}/{len(tests)})")
        print("📈 RAG EN")

        if basic_results:
            print(f"💰 Housing EN:")
            print(f"   EN: {basic_results['total_records']}")
            print(f"   EN: {basic_results['price_stats']['mean']:,.0f}")
            print(f"   EN-EN: {basic_results['correlations']['area']:.3f}")

        if advanced_results:
            print(f"\n🧠 EN:")
            perf = advanced_results["model_performance"]
            print(f"   R² EN: {perf['r2_score']:.3f}")
            print(f"   EN: {perf['mae']:,.0f}")

        if charts:
            print(f"\n📊 EN:")
            print(f"   EN: {len(charts)}")
            print(f"   EN: EN,EN,EN,EN")

        print("\n🔧 EN:")
        print("1. EN Docker EN: ./scripts/deploy/build_data_analysis_docker.sh")
        print("2. EN LangChain 1.0 EN")
        print("3. EN Docker EN")
        print("4. EN")

    else:
        print(f"\n⚠️ EN ({success_count}/{len(tests)})")
        print("🔧 EN:")
        print("- Docker EN")
        print("- Python EN")
        print("- EN")
        print("- EN")

    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
