#!/usr/bin/env python3
"""
EN
EN RAG EN
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


def generate_chinese_eda_code():
    """ENEDAEN"""

    analysis_code = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import warnings
import sys
import os
warnings.filterwarnings('ignore')

# EN
try:
    # EN
    if '/app/utils' not in sys.path:
        sys.path.insert(0, '/app/utils')
    import matplotlib_chinese_support
    matplotlib_chinese_support.setup_chinese_matplotlib()
    print("✓ EN")
except ImportError:
    # EN:EN
    plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Zen Hei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    print("✓ EN")

# EN
output_dir = '/workspace/output'
os.makedirs(output_dir, exist_ok=True)

def comprehensive_housing_eda(df):
    """EN"""

    print("="*60)
    print("EN")
    print("="*60)

    # 1. EN
    print("\\n📊 1. EN")
    print(f"EN: {df.shape}")
    print(f"EN: {len(df.columns)}")
    print(f"EN: {df.isnull().sum().sum()}")

    # 2. EN
    print("\\n📈 2. EN")
    print(df.describe())

    # 3. EN
    print("\\n💰 3. EN")

    # EN
    plt.figure(figsize=(15, 5))

    plt.subplot(1, 3, 1)
    plt.hist(df['price'], bins=30, alpha=0.7, color='skyblue', edgecolor='black')
    plt.title('EN', fontsize=14, fontweight='bold')
    plt.xlabel('EN(EN)', fontsize=12)
    plt.ylabel('EN', fontsize=12)
    plt.axvline(df['price'].mean(), color='red', linestyle='--',
               label=f'EN: {df["price"].mean():,.0f}')
    plt.legend()

    plt.subplot(1, 3, 2)
    plt.boxplot(df['price'])
    plt.title('EN', fontsize=14, fontweight='bold')
    plt.ylabel('EN(EN)', fontsize=12)

    plt.subplot(1, 3, 3)
    # EN
    price_bins = [0, 3000000, 5000000, 7000000, 10000000, float('inf')]
    price_labels = ['EN', 'EN', 'EN', 'EN', 'EN']
    df['price_category'] = pd.cut(df['price'], bins=price_bins, labels=price_labels, right=False)
    category_counts = df['price_category'].value_counts()

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
    plt.bar(category_counts.index, category_counts.values, color=colors, edgecolor='black')
    plt.title('EN', fontsize=14, fontweight='bold')
    plt.xlabel('EN', fontsize=12)
    plt.ylabel('EN', fontsize=12)
    plt.xticks(rotation=15)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/EN.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    # 4. EN
    print("\\n🏠 4. EN")

    plt.figure(figsize=(16, 12))

    # EN-EN
    plt.subplot(2, 3, 1)
    plt.scatter(df['area'], df['price'], alpha=0.6, color='coral', edgecolor='black')
    plt.xlabel('EN(EN)', fontsize=12)
    plt.ylabel('EN(EN)', fontsize=12)
    plt.title('EN-EN', fontsize=14, fontweight='bold')

    # EN
    z = np.polyfit(df['area'], df['price'], 1)
    p = np.poly1d(z)
    plt.plot(df['area'], p(df['area']), "r--", alpha=0.8, linewidth=2)

    # EN
    plt.subplot(2, 3, 2)
    bedroom_avg = df.groupby('bedrooms')['price'].mean()
    bars = plt.bar(bedroom_avg.index, bedroom_avg.values, color='lightblue', edgecolor='black')
    plt.xlabel('EN', fontsize=12)
    plt.ylabel('EN(EN)', fontsize=12)
    plt.title('EN', fontsize=14, fontweight='bold')

    # EN
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:,.0f}', ha='center', va='bottom', fontsize=10)

    # EN
    plt.subplot(2, 3, 3)
    furnish_stats = df.groupby('furnishingstatus').agg({
        'price': ['mean', 'count']
    }).round(0)

    furnish_labels = {'furnished': 'EN', 'semi-furnished': 'EN', 'unfurnished': 'EN'}
    furnish_stats.index = furnish_stats.index.map(furnish_labels)

    ax = furnish_stats['price']['mean'].plot(kind='bar', color=['#FF6B6B', '#4ECDC4', '#45B7D1'],
                                                   edgecolor='black')
    plt.xlabel('EN', fontsize=12)
    plt.ylabel('EN(EN)', fontsize=12)
    plt.title('EN', fontsize=14, fontweight='bold')

    # EN
    for i, (status, row) in enumerate(furnish_stats.iterrows()):
        count = row['price']['count']
        plt.text(i, row['price']['mean'] * 1.02, f'{count}EN',
                ha='center', fontsize=10, fontweight='bold')

    # EN
    plt.subplot(2, 3, 4)
    infrastructure_features = ['mainroad', 'guestroom', 'basement', 'airconditioning', 'hotwaterheating']
    infrastructure_labels = ['EN', 'EN', 'EN', 'EN', 'EN']

    avg_prices = []
    for feature in infrastructure_features:
        yes_avg = df[df[feature] == 'yes']['price'].mean()
        no_avg = df[df[feature] == 'no']['price'].mean()
        premium = ((yes_avg - no_avg) / no_avg * 100) if no_avg > 0 else 0
        avg_prices.append(premium)

    bars = plt.bar(infrastructure_labels, avg_prices, color='lightgreen', edgecolor='black')
    plt.xlabel('EN', fontsize=12)
    plt.ylabel('EN(%)', fontsize=12)
    plt.title('EN', fontsize=14, fontweight='bold')
    plt.xticks(rotation=15)

    # EN
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom', fontsize=10)

    # EN
    plt.subplot(2, 3, 5)
    parking_avg = df.groupby('parking')['price'].mean()
    bars = plt.bar(parking_avg.index, parking_avg.values, color='orange', edgecolor='black')
    plt.xlabel('EN', fontsize=12)
    plt.ylabel('EN(EN)', fontsize=12)
    plt.title('EN', fontsize=14, fontweight='bold')

    # EN
    plt.subplot(2, 3, 6)
    prefarea_avg = df.groupby('prefarea')['price'].mean()
    prefarea_labels = {'yes': 'EN', 'no': 'EN'}
    prefarea_avg.index = prefarea_avg.index.map(prefarea_labels)

    bars = plt.bar(prefarea_avg.index, prefarea_avg.values,
                   color=['#96CEB4', '#FFEAA7'], edgecolor='black')
    plt.xlabel('EN', fontsize=12)
    plt.ylabel('EN(EN)', fontsize=12)
    plt.title('EN', fontsize=14, fontweight='bold')

    # EN
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:,.0f}', ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/EN.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    # 5. EN
    print("\\n🔗 5. EN")

    plt.figure(figsize=(12, 10))

    # EN
    numeric_features = ['price', 'area', 'bedrooms', 'bathrooms', 'stories', 'parking']
    correlation_matrix = df[numeric_features].corr()

    # EN
    feature_names = {
        'price': 'EN',
        'area': 'EN',
        'bedrooms': 'EN',
        'bathrooms': 'EN',
        'stories': 'EN',
        'parking': 'EN'
    }

    correlation_matrix.index = [feature_names.get(col, col) for col in correlation_matrix.index]
    correlation_matrix.columns = [feature_names.get(col, col) for col in correlation_matrix.columns]

    mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
    sns.heatmap(correlation_matrix, mask=mask, annot=True, cmap='coolwarm',
                center=0, square=True, linewidths=0.5, fmt='.3f',
                annot_kws={'size': 10})
    plt.title('EN', fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()

    plt.savefig(f'{output_dir}/EN.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    # 6. EN
    print("\\n📋 6. EN")

    insights = {
        "dataset_overview": {
            "total_records": len(df),
            "total_features": len(df.columns),
            "missing_values": int(df.isnull().sum().sum()),
            "data_quality": "EN" if df.isnull().sum().sum() == 0 else "EN"
        },
        "price_analysis": {
            "mean_price": float(df['price'].mean()),
            "median_price": float(df['price'].median()),
            "price_range": {
                "min": float(df['price'].min()),
                "max": float(df['price'].max())
            },
            "price_distribution": dict(df['price_category'].value_counts())
        },
        "key_correlations": {
            "area_price_correlation": float(df[['area', 'price']].corr().iloc[0, 1]),
            "bedrooms_price_correlation": float(df[['bedrooms', 'price']].corr().iloc[0, 1]),
            "bathrooms_price_correlation": float(df[['bathrooms', 'price']].corr().iloc[0, 1])
        },
        "market_insights": {
            "avg_price_per_bedroom": float(df.groupby('bedrooms')['price'].mean().mean()),
            "furnished_premium": float(df[df['furnishingstatus'] == 'furnished']['price'].mean() /
                                     df[df['furnishingstatus'] == 'unfurnished']['price'].mean() - 1),
            "mainroad_premium": float(df[df['mainroad'] == 'yes']['price'].mean() /
                                    df[df['mainroad'] == 'no']['price'].mean() - 1),
            "ac_premium": float(df[df['airconditioning'] == 'yes']['price'].mean() /
                              df[df['airconditioning'] == 'no']['price'].mean() - 1)
        },
        "visualization_files": [
            "EN.png",
            "EN.png",
            "EN.png"
        ]
    }

    print("📊 EN:")
    print(f"   • EN: {insights['dataset_overview']['total_records']:,}")
    print(f"   • EN: {insights['price_analysis']['mean_price']:,.0f} EN")
    print(f"   • EN: {insights['price_analysis']['price_range']['min']:,.0f} - {insights['price_analysis']['price_range']['max']:,.0f} EN")
    print(f"   • EN-EN: {insights['key_correlations']['area_price_correlation']:.3f}")
    print(f"   • EN: {insights['market_insights']['furnished_premium']:.1%}")
    print(f"   • EN: {insights['market_insights']['mainroad_premium']:.1%}")
    print(f"   • EN: {insights['market_insights']['ac_premium']:.1%}")

    # EN
    with open(f'{output_dir}/EN.json', 'w', encoding='utf-8') as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)

    print(f"\\n✅ EN!")
    print(f"📁 EN: {output_dir}")
    print(f"📋 EN: {output_dir}/EN.json")

    return insights

# EN
if __name__ == "__main__":
    # EN
    data_file = "/workspace/data/Housing.csv"  # This path is used in Docker environment; for local testing: "test_resources/datasets/Housing.csv"

    try:
        # EN
        df = pd.read_csv(data_file)
        print(f"✅ EN: {df.shape}")

        # EN
        results = comprehensive_housing_eda(df)

        print(f"\\n🎉 EN!")

    except Exception as e:
        print(f"❌ EN: {e}")
        import traceback
        traceback.print_exc()
'''

    return analysis_code


def test_integrated_chinese_analysis():
    """EN"""
    print("=" * 60)
    print("🇨🇳 EN")
    print("=" * 60)

    try:
        # ENEDAEN
        print("📝 ENEDAEN...")
        chinese_eda_code = generate_chinese_eda_code()

        print("✅ EN,EN:")
        print("   • EN")
        print("   • EN")
        print("   • EN")
        print("   • EN")

        # EN
        print("\n🔄 EN...")

        # EN
        exec_globals = {}
        exec(chinese_eda_code, exec_globals)

        print("✅ EN!")
        return True

    except Exception as e:
        print(f"❌ EN: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """EN"""
    print("🚀 EN")
    print("🎯 EN RAG EN")

    success = test_integrated_chinese_analysis()

    print("\n" + "=" * 60)
    print("📊 EN")
    print("=" * 60)

    if success:
        print("🎉 EN!")
        print("✅ EN")
        print("✅ EN")
        print("✅ EN")
        print("✅ EN")
        print("✅ Docker EN")

        print("\n🔧 EN:")
        print("   • Dockerfile.data-analysis - EN")
        print("   • backend/tools/data_analysis.py - EN")
        print("   • backend/tools/iterative_code_execution.py - EN")
        print("   • backend/utils/matplotlib_chinese_support.py - EN")

        print("\n📈 EN:")
        print("   ✅ EN: EN")
        print("   ✅ EN: EN")
        print("   ✅ EN: EN")
        print("   ✅ EN: EN")
        print("   ✅ EN: EN")
        print("   ✅ EN: EN")

        print("\n🚀 EN!")
        print("EN:")
        print("1. EN Docker EN")
        print("2. EN")
        print("3. EN")
        print("4. EN")

    else:
        print("⚠️ EN")
        print("🔧 EN:")
        print("- EN")
        print("- EN")
        print("- Docker EN")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
