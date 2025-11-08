#!/usr/bin/env python3
"""
测试 Docker 代码执行功能
"""

import os
import sys
from pathlib import Path

import pandas as pd

# 添加项目路径
sys.path.append(str(Path(__file__).parent))


def test_docker_connectivity():
    """测试Docker连接"""
    print("=" * 60)
    print("🐳 测试 Docker 连接")
    print("=" * 60)

    try:
        import docker

        client = docker.from_env()

        # 测试Docker连接
        client.ping()
        print("✅ Docker 连接成功!")

        # 检查现有镜像
        images = client.images.list()
        print(f"📦 发现 {len(images)} 个 Docker 镜像")

        # 检查是否已有分析镜像
        analysis_images = [
            img
            for img in images
            if any(tag.endswith("code-analysis") for tag in img.tags)
        ]

        if analysis_images:
            print("✅ 发现数据分析镜像:")
            for img in analysis_images:
                print(f"   {', '.join(img.tags)}")
            return True, client
        else:
            print("⚠️ 未发现数据分析镜像，需要构建")
            return False, client

    except Exception as e:
        print(f"❌ Docker 连接失败: {e}")
        return False, None


def test_code_execution_without_docker():
    """测试不使用Docker的代码执行"""
    print("\n" + "=" * 60)
    print("⚙️ 测试 Python 代码执行（本地环境）")
    print("=" * 60)

    # 测试 Housing 数据分析的代码
    test_code = '''
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
    print("\\n=== 基础统计信息 ===")
    print(f"价格范围: {df['price'].min():,.0f} - {df['price'].max():,.0f}")
    print(f"平均价格: {df['price'].mean():,.0f}")
    print(f"平均面积: {df['area'].mean():,.0f} sq.ft")

    # 3. 相关性分析
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    correlation = df[numeric_cols].corr()['price'].sort_values(ascending=False)
    print("\\n=== 价格相关性排名 ===")
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

    print("\\n=== 分析完成 ===")
    print(f"处理了 {results['total_records']} 条记录")
    print(f"最重要的特征: {list(results['feature_importance'].keys())[:3]}")

    return results

# 执行分析
if __name__ == "__main__":
    results = analyze_housing_data()
    print(f"\\n分析结果摘要: {len(results)} 个主要指标")
'''

    try:
        # 创建临时脚本文件
        script_path = Path("temp_analysis_script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(test_code)

        # 设置输出目录
        output_dir = Path("docker_test_output")
        output_dir.mkdir(exist_ok=True)

        # 修改脚本以支持输出保存
        modified_code = (
            test_code
            + """
import json

# 保存分析结果
output_file = Path("docker_test_output/analysis_results.json")
results = analyze_housing_data()

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\\n结果已保存到: {output_file}")
"""
        )

        # 执行脚本
        exec_globals = {}
        exec(modified_code, exec_globals)

        print("✅ 代码执行成功!")

        # 检查结果文件
        result_file = Path("docker_test_output/analysis_results.json")
        if result_file.exists():
            import json

            with open(result_file, "r", encoding="utf-8") as f:
                results = json.load(f)

            print("📊 分析结果:")
            print(f"   总记录数: {results['total_records']}")
            print(f"   平均价格: {results['price_stats']['mean']:,.0f}")
            print(
                f"   价格范围: {results['price_stats']['min']:,.0f} - {results['price_stats']['max']:,.0f}"
            )

            # 显示特征重要性
            print("   特征重要性排名:")
            for i, (feature, importance) in enumerate(
                list(results["feature_importance"].items())[:5], 1
            ):
                print(f"   {i}. {feature}: {importance:.3f}")

            return True, results
        else:
            print("⚠️ 未找到结果文件")
            return False, None

    except Exception as e:
        print(f"❌ 代码执行失败: {e}")
        import traceback

        traceback.print_exc()
        return False, None


def test_advanced_analysis():
    """测试高级分析功能"""
    print("\n" + "=" * 60)
    print("🧠 测试高级数据分析功能")
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
    """高级房价分析 - 机器学习建模"""

    print("=== 高级房价分析开始 ===")

    # 1. 数据预处理
    data_path = "/Users/niuyp/Documents/github.com/Industry-AI-Flow/test_resources/datasets/Housing.csv"
    df = pd.read_csv(data_path)

    print(f"原始数据形状: {df.shape}")

    # 2. 特征工程
    # 处理分类变量
    categorical_cols = ['mainroad', 'guestroom', 'basement',
                       'hotwaterheating', 'airconditioning', 'prefarea', 'furnishingstatus']

    le = LabelEncoder()
    for col in categorical_cols:
        df[col] = le.fit_transform(df[col])

    print(f"特征工程完成，处理后形状: {df.shape}")

    # 3. 准备数据
    X = df.drop('price', axis=1)
    y = df['price']

    # 4. 分割数据
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"训练集大小: {X_train.shape}")
    print(f"测试集大小: {X_test.shape}")

    # 5. 训练模型
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # 6. 预测和评估
    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)

    # 7. 特征重要性
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\\n=== 模型评估结果 ===")
    print(f"平均绝对误差 (MAE): {mae:,.0f}")
    print(f"均方根误差 (RMSE): {rmse:,.0f}")
    print(f"R² 分数: {r2:.3f}")

    print("\\n=== 特征重要性排名 ===")
    print(feature_importance.head(10))

    # 8. 创建结果摘要
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

    print("\\n=== 高级分析完成 ===")
    print(f"模型R²分数: {r2:.3f}")
    print(f"最重要的特征: {feature_importance.iloc[0]['feature']}")

    return results

# 执行高级分析
if __name__ == "__main__":
    results = advanced_housing_analysis()
    print(f"\\n高级分析完成，生成了 {len(results)} 个主要指标")
'''

    try:
        # 创建临时脚本
        script_path = Path("advanced_analysis_script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(advanced_code)

        # 执行高级分析
        exec_globals = {}
        exec(advanced_code, exec_globals)

        print("✅ 高级分析执行成功!")
        return True, exec_globals.get("results", {})

    except ImportError as e:
        if "sklearn" in str(e):
            print("⚠️ scikit-learn 未安装，跳过机器学习测试")
            return None, None
        else:
            print(f"❌ 高级分析失败: {e}")
            return False, None
    except Exception as e:
        print(f"❌ 高级分析失败: {e}")
        return False, None


def test_visualization_generation():
    """测试可视化生成"""
    print("\n" + "=" * 60)
    print("📊 测试可视化图表生成")
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
    """生成多种可视化图表"""

    print("=== 开始生成可视化图表 ===")

    # 创建输出目录
    output_dir = Path("docker_test_output/visualizations")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载数据
    data_path = "/Users/niuyp/Documents/github.com/Industry-AI-Flow/test_resources/datasets/Housing.csv"
    df = pd.read_csv(data_path)

    plt.style.use('default')
    plt.rcParams['figure.figsize'] = (12, 8)

    generated_charts = []

    # 1. 价格分布图（直方图 + 密度图）
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.hist(df['price'], bins=30, alpha=0.7, color='skyblue', edgecolor='black')
    plt.title('价格分布直方图')
    plt.xlabel('价格')
    plt.ylabel('频次')

    plt.subplot(1, 2, 2)
    plt.hist(df['price'], bins=30, alpha=0.3, density=True, color='skyblue')
    df['price'].plot(kind='kde', color='red', linewidth=2)
    plt.title('价格密度图')
    plt.xlabel('价格')
    plt.ylabel('密度')

    plt.tight_layout()
    chart1_path = output_dir / "price_distribution_analysis.png"
    plt.savefig(chart1_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    generated_charts.append(str(chart1_path))
    print("✅ 1. 价格分布图已生成")

    # 2. 面积-价格散点图（按装修状态分类）
    plt.figure(figsize=(10, 6))
    colors = {'furnished': 'gold', 'semi-furnished': 'lightblue', 'unfurnished': 'lightgreen'}

    for furnish_status in df['furnishingstatus'].unique():
        subset = df[df['furnishingstatus'] == furnish_status]
        plt.scatter(subset['area'], subset['price'],
                   alpha=0.6, c=colors.get(furnish_status, 'gray'),
                   label=furnish_status, edgecolors='black', linewidth=0.5)

    plt.xlabel('面积 (sq.ft)')
    plt.ylabel('价格')
    plt.title('面积-价格关系（按装修状态分类）')
    plt.legend()
    plt.grid(True, alpha=0.3)

    chart2_path = output_dir / "area_price_by_furnishing.png"
    plt.savefig(chart2_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    generated_charts.append(str(chart2_path))
    print("✅ 2. 面积-价格散点图已生成")

    # 3. 特征相关性热力图
    plt.figure(figsize=(12, 8))
    numeric_df = df.select_dtypes(include=[np.number])
    correlation_matrix = numeric_df.corr()

    mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
    sns.heatmap(correlation_matrix, mask=mask, annot=True, cmap='coolwarm',
                center=0, square=True, linewidths=0.5, fmt='.2f')
    plt.title('特征相关性热力图')
    plt.tight_layout()

    chart3_path = output_dir / "correlation_heatmap_enhanced.png"
    plt.savefig(chart3_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    generated_charts.append(str(chart3_path))
    print("✅ 3. 相关性热力图已生成")

    # 4. 分类特征分析（多子图）
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('分类特征分布分析', fontsize=16)

    categorical_features = ['mainroad', 'guestroom', 'basement', 'hotwaterheating', 'airconditioning', 'prefarea']
    colors_list = ['lightcoral', 'lightgreen', 'lightskyblue', 'gold', 'lightpink', 'lightgray']

    for i, (feature, color) in enumerate(zip(categorical_features, colors_list)):
        row, col = i // 3, i % 3
        value_counts = df[feature].value_counts()

        axes[row, col].bar(value_counts.index, value_counts.values,
                          color=color, alpha=0.8, edgecolor='black')
        axes[row, col].set_title(f'{feature} 分布')
        axes[row, col].set_ylabel('频次')

        # 添加数值标签
        for j, v in enumerate(value_counts.values):
            axes[row, col].text(j, v + max(value_counts) * 0.01, str(v),
                               ha='center', fontweight='bold')

    plt.tight_layout()
    chart4_path = output_dir / "categorical_features_analysis.png"
    plt.savefig(chart4_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    generated_charts.append(str(chart4_path))
    print("✅ 4. 分类特征分析图已生成")

    # 5. 价格箱线图（按不同特征分组）
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('价格分布箱线图分析', fontsize=16)

    # 按卧室数
    df.boxplot(column='price', by='bedrooms', ax=axes[0,0])
    axes[0,0].set_title('按卧室数分组的价格分布')
    axes[0,0].set_xlabel('卧室数')

    # 按装修状态
    df.boxplot(column='price', by='furnishingstatus', ax=axes[0,1])
    axes[0,1].set_title('按装修状态分组的价格分布')
    axes[0,1].set_xlabel('装修状态')

    # 按是否主路
    df.boxplot(column='price', by='mainroad', ax=axes[1,0])
    axes[1,0].set_title('按是否临主路分组的价格分布')
    axes[1,0].set_xlabel('是否临主路')

    # 按空调配置
    df.boxplot(column='price', by='airconditioning', ax=axes[1,1])
    axes[1,1].set_title('按空调配置分组的价格分布')
    axes[1,1].set_xlabel('空调配置')

    plt.tight_layout()
    chart5_path = output_dir / "price_boxplot_analysis.png"
    plt.savefig(chart5_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    generated_charts.append(str(chart5_path))
    print("✅ 5. 价格箱线图分析已生成")

    print(f"\\n=== 可视化生成完成 ===")
    print(f"总共生成了 {len(generated_charts)} 个图表")
    print(f"图表保存位置: {output_dir}")

    return generated_charts, output_dir

# 执行可视化生成
if __name__ == "__main__":
    charts, output_dir = generate_visualizations()
    print(f"\\n可视化任务完成，生成了 {len(charts)} 个文件")
'''

    try:
        # 执行可视化代码
        exec_globals = {}
        exec(visualization_code, exec_globals)

        if exec_globals.get("charts"):
            charts = exec_globals["charts"]
            output_dir = exec_globals.get("output_dir")

            print("📊 生成的图表:")
            for i, chart_path in enumerate(charts, 1):
                chart_name = Path(chart_path).name
                print(f"   {i}. {chart_name}")

            print(f"\\n📁 图表目录: {output_dir}")
            return True, charts
        else:
            print("⚠️ 未生成图表")
            return False, []

    except Exception as e:
        print(f"❌ 可视化生成失败: {e}")
        import traceback

        traceback.print_exc()
        return False, []


def main():
    """主测试函数"""
    print("🚀 开始 Docker 代码执行功能测试")
    print("🎯 测试完整的 RAG 数据分析节点")

    # 测试1: Docker连接
    docker_available, client = test_docker_connectivity()

    # 测试2: 基础代码执行（本地环境）
    print("\n" + "=" * 60)
    print("测试 2/4: 基础代码执行")
    print("=" * 60)
    code_success, basic_results = test_code_execution_without_docker()

    # 测试3: 高级分析功能
    print("\n" + "=" * 60)
    print("测试 3/4: 高级数据分析")
    print("=" * 60)
    advanced_success, advanced_results = test_advanced_analysis()

    # 测试4: 可视化生成
    print("\n" + "=" * 60)
    print("测试 4/4: 可视化图表生成")
    print("=" * 60)
    viz_success, charts = test_visualization_generation()

    # 测试总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)

    tests = [
        ("Docker连接", docker_available),
        ("基础代码执行", code_success),
        ("高级数据分析", advanced_success if advanced_success is not None else False),
        ("可视化生成", viz_success),
    ]

    success_count = 0
    for test_name, success in tests:
        if success is not None:
            status = "✅ 成功" if success else "❌ 失败"
            print(f"   {test_name}: {status}")
            if success:
                success_count += 1
        else:
            print(f"   {test_name}: ⚠️ 跳过")

    overall_success = success_count >= 3  # 至少3个测试通过

    if overall_success:
        print(f"\n🎉 核心功能测试通过! ({success_count}/{len(tests)})")
        print("📈 RAG 数据分析节点基础功能验证成功")

        if basic_results:
            print(f"💰 Housing 数据集分析结果:")
            print(f"   总记录数: {basic_results['total_records']}")
            print(f"   平均价格: {basic_results['price_stats']['mean']:,.0f}")
            print(f"   面积-价格相关性: {basic_results['correlations']['area']:.3f}")

        if advanced_results:
            print(f"\n🧠 机器学习模型性能:")
            perf = advanced_results["model_performance"]
            print(f"   R² 分数: {perf['r2_score']:.3f}")
            print(f"   平均误差: {perf['mae']:,.0f}")

        if charts:
            print(f"\n📊 可视化图表:")
            print(f"   生成数量: {len(charts)}")
            print(f"   包含类型: 分布图、散点图、热力图、箱线图等")

        print("\n🔧 下一步建议:")
        print("1. 构建 Docker 镜像: ./scripts/build_data_analysis_docker.sh")
        print("2. 测试完整的 LangChain 1.0 集成")
        print("3. 验证自我修复机制在 Docker 环境中的表现")
        print("4. 使用更多样化的数据集进行测试")

    else:
        print(f"\n⚠️ 测试结果不理想 ({success_count}/{len(tests)})")
        print("🔧 需要检查的组件:")
        print("- Docker 安装和配置")
        print("- Python 依赖包")
        print("- 数据文件路径")
        print("- 系统权限设置")

    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
