
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 设置matplotlib
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['savefig.dpi'] = 150
plt.rcParams['figure.dpi'] = 100

def analyze_housing_data():
    """分析房价数据"""

    print("=== 房价数据分析开始 ===")

    # 1. 加载数据
    data_path = "/Users/niuyp/Documents/github.com/Industry-AI-Flow/test_resources/datasets/Housing.csv"
    df = pd.read_csv(data_path)

    print(f"数据加载成功: {df.shape}")
    print(f"列名: {list(df.columns)}")

    # 2. 基础统计
    print("\n=== 基础统计信息 ===")
    print(f"价格范围: {df['price'].min():,.0f} - {df['price'].max():,.0f}")
    print(f"平均价格: {df['price'].mean():,.0f}")
    print(f"平均面积: {df['area'].mean():,.0f} sq.ft")

    # 3. 相关性分析
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    correlation = df[numeric_cols].corr()['price'].sort_values(ascending=False)
    print("\n=== 价格相关性排名 ===")
    for feature, corr in correlation.items():
        if feature != 'price':
            print(f"{feature}: {corr:.3f}")

    # 4. 创建分析结果
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

    print("\n=== 分析完成 ===")
    print(f"处理了 {results['total_records']} 条记录")
    print(f"最重要的特征: {list(results['feature_importance'].keys())[:3]}")

    return results

# 执行分析
if __name__ == "__main__":
    results = analyze_housing_data()
    print(f"\n分析结果摘要: {len(results)} 个主要指标")
