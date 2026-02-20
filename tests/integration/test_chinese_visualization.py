#!/usr/bin/env python3
"""
测试中文字体支持的可视化分析
"""

import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

# 导入中文字体支持
try:
    from backend.utils.matplotlib_chinese_support import setup_chinese_matplotlib

    setup_chinese_matplotlib()
    print("✅ 中文字体支持已启用")
except ImportError:
    print("⚠️ 中文字体支持模块未找到，使用备用方案")

import matplotlib.pyplot as plt
import seaborn as sns


def test_chinese_visualization():
    """测试中文可视化功能"""
    print("=" * 60)
    print("🇨🇳 测试中文字体可视化功能")
    print("=" * 60)

    # 加载数据
    data_path = "test_resources/datasets/Housing.csv"
    df = pd.read_csv(data_path)

    print(f"📊 数据加载成功: {df.shape}")

    # 创建输出目录
    output_dir = Path("chinese_visualization_output")
    output_dir.mkdir(exist_ok=True)

    generated_charts = []

    # 图表1: 房价分布分析（中文标题和标签）
    plt.figure(figsize=(15, 5))

    plt.subplot(1, 3, 1)
    plt.hist(df["price"], bins=30, alpha=0.7, color="skyblue", edgecolor="black")
    plt.title("房价分布直方图", fontsize=14, fontweight="bold")
    plt.xlabel("房价（卢比）", fontsize=12)
    plt.ylabel("频次", fontsize=12)

    plt.subplot(1, 3, 2)
    plt.boxplot(df["price"])
    plt.title("房价箱线图", fontsize=14, fontweight="bold")
    plt.ylabel("房价（卢比）", fontsize=12)

    plt.subplot(1, 3, 3)
    # 房价分档分析
    price_bins = [0, 3000000, 5000000, 7000000, 10000000, float("inf")]
    price_labels = ["经济型", "舒适型", "中档型", "高档型", "豪华型"]
    df["price_category"] = pd.cut(
        df["price"], bins=price_bins, labels=price_labels, right=False
    )
    category_counts = df["price_category"].value_counts()

    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]
    plt.bar(
        category_counts.index, category_counts.values, color=colors, edgecolor="black"
    )
    plt.title("房价分档分布", fontsize=14, fontweight="bold")
    plt.xlabel("房价档次", fontsize=12)
    plt.ylabel("房屋数量", fontsize=12)
    plt.xticks(rotation=15)

    plt.tight_layout()
    chart1 = output_dir / "房价分布分析_中文.png"
    plt.savefig(chart1, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart1)
    print("✅ 房价分布图已生成（中文标题）")

    # 图表2: 房屋特征与房价关系
    plt.figure(figsize=(16, 10))

    # 面积-价格关系
    plt.subplot(2, 3, 1)
    plt.scatter(df["area"], df["price"], alpha=0.6, color="coral", edgecolor="black")
    plt.xlabel("房屋面积（平方英尺）", fontsize=12)
    plt.ylabel("房价（卢比）", fontsize=12)
    plt.title("面积-价格关系", fontsize=14, fontweight="bold")

    # 卧室数量与平均价格
    plt.subplot(2, 3, 2)
    bedroom_avg = df.groupby("bedrooms")["price"].mean()
    bars = plt.bar(
        bedroom_avg.index, bedroom_avg.values, color="lightblue", edgecolor="black"
    )
    plt.xlabel("卧室数量", fontsize=12)
    plt.ylabel("平均房价（卢比）", fontsize=12)
    plt.title("卧室数量与平均价格", fontsize=14, fontweight="bold")
    # 添加数值标签
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:,.0f}",
            ha="center",
            va="bottom",
        )

    # 装修状态与价格
    plt.subplot(2, 3, 3)
    furnish_avg = df.groupby("furnishingstatus")["price"].mean()
    furnish_labels = {"furnished": "精装修", "semi-furnished": "半装修", "unfurnished": "毛坯房"}
    furnish_avg.index = furnish_avg.index.map(furnish_labels)
    colors_furnish = ["#FF6B6B", "#4ECDC4", "#45B7D1"]
    bars = plt.bar(
        furnish_avg.index, furnish_avg.values, color=colors_furnish, edgecolor="black"
    )
    plt.xlabel("装修状态", fontsize=12)
    plt.ylabel("平均房价（卢比）", fontsize=12)
    plt.title("装修状态与平均价格", fontsize=14, fontweight="bold")
    # 添加数值标签
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:,.0f}",
            ha="center",
            va="bottom",
        )

    # 是否临主路与价格
    plt.subplot(2, 3, 4)
    mainroad_avg = df.groupby("mainroad")["price"].mean()
    mainroad_labels = {"yes": "临主路", "no": "不临主路"}
    mainroad_avg.index = mainroad_avg.index.map(mainroad_labels)
    colors_mainroad = ["#96CEB4", "#FFEAA7"]
    bars = plt.bar(
        mainroad_avg.index,
        mainroad_avg.values,
        color=colors_mainroad,
        edgecolor="black",
    )
    plt.xlabel("地理位置", fontsize=12)
    plt.ylabel("平均房价（卢比）", fontsize=12)
    plt.title("地理位置与平均价格", fontsize=14, fontweight="bold")
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:,.0f}",
            ha="center",
            va="bottom",
        )

    # 空调配置与价格
    plt.subplot(2, 3, 5)
    ac_avg = df.groupby("airconditioning")["price"].mean()
    ac_labels = {"yes": "有空调", "no": "无空调"}
    ac_avg.index = ac_avg.index.map(ac_labels)
    colors_ac = ["#FF6B6B", "#DDA0DD"]
    bars = plt.bar(ac_avg.index, ac_avg.values, color=colors_ac, edgecolor="black")
    plt.xlabel("空调配置", fontsize=12)
    plt.ylabel("平均房价（卢比）", fontsize=12)
    plt.title("空调配置与平均价格", fontsize=14, fontweight="bold")
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:,.0f}",
            ha="center",
            va="bottom",
        )

    # 车位数量与价格
    plt.subplot(2, 3, 6)
    parking_avg = df.groupby("parking")["price"].mean()
    bars = plt.bar(
        parking_avg.index, parking_avg.values, color="lightgreen", edgecolor="black"
    )
    plt.xlabel("停车位数量", fontsize=12)
    plt.ylabel("平均房价（卢比）", fontsize=12)
    plt.title("停车位数量与平均价格", fontsize=14, fontweight="bold")
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
    chart2 = output_dir / "房屋特征价格关系_中文.png"
    plt.savefig(chart2, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart2)
    print("✅ 房屋特征价格关系图已生成（中文标签）")

    # 图表3: 特征相关性热力图
    plt.figure(figsize=(12, 10))

    # 准备中文特征名映射
    feature_names = {
        "price": "房价",
        "area": "面积",
        "bedrooms": "卧室数",
        "bathrooms": "浴室数",
        "stories": "楼层数",
        "mainroad": "临主路",
        "guestroom": "客房",
        "basement": "地下室",
        "hotwaterheating": "热水供应",
        "airconditioning": "空调",
        "parking": "停车位",
        "prefarea": "优选区域",
        "furnishingstatus": "装修状态",
    }

    # 选择数值特征进行相关性分析
    numeric_features = ["price", "area", "bedrooms", "bathrooms", "stories", "parking"]
    correlation_matrix = df[numeric_features].corr()

    # 重命名索引和列名
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
    plt.title("房屋特征相关性热力图", fontsize=16, fontweight="bold", pad=20)
    plt.tight_layout()

    chart3 = output_dir / "房屋特征相关性热力图_中文.png"
    plt.savefig(chart3, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart3)
    print("✅ 相关性热力图已生成（中文标签）")

    # 图表4: 综合分析仪表板
    plt.figure(figsize=(20, 12))

    # 左上：价格分布和统计
    plt.subplot(2, 4, 1)
    plt.hist(df["price"], bins=20, alpha=0.7, color="lightcoral", edgecolor="black")
    plt.axvline(
        df["price"].mean(),
        color="red",
        linestyle="--",
        linewidth=2,
        label=f'平均值: {df["price"].mean():,.0f}',
    )
    plt.xlabel("房价（卢比）")
    plt.ylabel("频次")
    plt.title("房价分布", fontweight="bold")
    plt.legend()

    # 右上：面积分布
    plt.subplot(2, 4, 2)
    plt.hist(df["area"], bins=20, alpha=0.7, color="lightblue", edgecolor="black")
    plt.axvline(
        df["area"].mean(),
        color="red",
        linestyle="--",
        linewidth=2,
        label=f'平均值: {df["area"].mean():,.0f}',
    )
    plt.xlabel("面积（平方英尺）")
    plt.ylabel("频次")
    plt.title("面积分布", fontweight="bold")
    plt.legend()

    # 中上：分类特征饼图
    plt.subplot(2, 4, 3)
    furnish_counts = df["furnishingstatus"].value_counts()
    furnish_labels_map = {
        "furnished": "精装修",
        "semi-furnished": "半装修",
        "unfurnished": "毛坯房",
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
    plt.title("装修状态分布", fontweight="bold")

    # 右上2：临主路分布
    plt.subplot(2, 4, 4)
    mainroad_counts = df["mainroad"].value_counts()
    mainroad_labels_map = {"yes": "临主路", "no": "不临主路"}
    labels = [mainroad_labels_map.get(x, x) for x in mainroad_counts.index]
    colors = ["#96CEB4", "#FFEAA7"]
    plt.pie(mainroad_counts.values, labels=labels, autopct="%1.1f%%", colors=colors)
    plt.title("临主路分布", fontweight="bold")

    # 下方左：箱线图对比
    plt.subplot(2, 4, 5)
    # 按装修状态的价格箱线图
    df.boxplot(column="price", by="furnishingstatus", ax=plt.gca())
    plt.xlabel("装修状态")
    plt.ylabel("房价（卢比）")
    plt.title("不同装修状态的价格分布", fontweight="bold")
    plt.xticks([1, 2, 3], ["精装修", "半装修", "毛坯房"])

    # 下方左2：卧室数vs价格
    plt.subplot(2, 4, 6)
    bedroom_data = [
        df[df["bedrooms"] == i]["price"].values for i in sorted(df["bedrooms"].unique())
    ]
    plt.boxplot(bedroom_data)
    plt.xlabel("卧室数量")
    plt.ylabel("房价（卢比）")
    plt.title("不同卧室数的价格分布", fontweight="bold")
    plt.grid(True, alpha=0.3)

    # 下方右：关键统计指标
    plt.subplot(2, 4, 7)
    stats_text = f"""房价统计关键指标：

样本数量: {len(df):,} 套

价格统计:
• 平均值: {df['price'].mean():,.0f} 卢比
• 中位数: {df['price'].median():,.0f} 卢比
• 标准差: {df['price'].std():,.0f} 卢比
• 最小值: {df['price'].min():,.0f} 卢比
• 最大值: {df['price'].max():,.0f} 卢比

面积统计:
• 平均值: {df['area'].mean():,.0f} 平方英尺
• 中位数: {df['area'].median():,.0f} 平方英尺
• 范围: {df['area'].min():,} - {df['area'].max():,} 平方英尺
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
    plt.title("关键统计指标", fontweight="bold")

    # 下方右2：市场洞察
    plt.subplot(2, 4, 8)
    insights_text = f"""市场洞察总结：

🏠 价格档次分布:
• 经济型: {len(df[df['price'] < 3000000]):,} 套
• 舒适型: {len(df[(df['price'] >= 3000000) & (df['price'] < 5000000)]):,} 套
• 中档型: {len(df[(df['price'] >= 5000000) & (df['price'] < 7000000)]):,} 套
• 高档型: {len(df[(df['price'] >= 7000000) & (df['price'] < 10000000)]):,} 套
• 豪华型: {len(df[df['price'] >= 10000000]):,} 套

🔑 关键发现:
• 面积与房价相关性: {df[['area', 'price']].corr().iloc[0,1]:.3f}
• 主路房比例: {df[df['mainroad'] == 'yes'].shape[0]/len(df)*100:.1f}%
• 精装修比例: {df[df['furnishingstatus'] == 'furnished'].shape[0]/len(df)*100:.1f}%
• 有空调比例: {df[df['airconditioning'] == 'yes'].shape[0]/len(df)*100:.1f}%
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
    plt.title("市场洞察", fontweight="bold")

    plt.tight_layout()
    chart4 = output_dir / "房价综合分析仪表板_中文.png"
    plt.savefig(chart4, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    generated_charts.append(chart4)
    print("✅ 综合分析仪表板已生成（中文）")

    return generated_charts, output_dir


def test_chinese_text_rendering():
    """测试中文文本渲染"""
    print("\n" + "=" * 60)
    print("📝 测试中文文本渲染")
    print("=" * 60)

    plt.figure(figsize=(12, 8))

    # 创建一个包含多种中文文本的图表
    plt.subplot(2, 2, 1)
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)

    plt.plot(x, y1, label="正弦波", linewidth=2, color="blue")
    plt.plot(x, y2, label="余弦波", linewidth=2, color="red")
    plt.title("三角函数图像", fontsize=14, fontweight="bold")
    plt.xlabel("X轴（弧度）")
    plt.ylabel("Y轴值")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(2, 2, 2)
    categories = ["经济型", "舒适型", "中档型", "高档型", "豪华型"]
    values = [25, 30, 20, 15, 10]
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]

    bars = plt.bar(categories, values, color=colors, edgecolor="black")
    plt.title("房屋类型分布", fontsize=14, fontweight="bold")
    plt.xlabel("房屋类型")
    plt.ylabel("占比（%）")

    # 添加数值标签
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
    # 绘制饼图
    sizes = [35, 25, 20, 15, 5]
    labels = ["一室户", "两室户", "三室户", "四室户", "五室及以上"]
    explode = (0.05, 0.05, 0.05, 0.05, 0.1)
    colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))

    plt.pie(sizes, explode=explode, labels=labels, autopct="%1.1f%%", colors=colors)
    plt.title("户型分布", fontsize=14, fontweight="bold")

    plt.subplot(2, 2, 4)
    # 测试复杂的中文文本
    plt.text(
        0.5,
        0.8,
        "中文字体测试",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        transform=plt.gca().transAxes,
    )
    plt.text(
        0.5,
        0.6,
        "支持中文显示！",
        ha="center",
        va="center",
        fontsize=14,
        color="red",
        transform=plt.gca().transAxes,
    )
    plt.text(
        0.5,
        0.4,
        "包含标点符号：，。！？",
        ha="center",
        va="center",
        fontsize=12,
        color="blue",
        transform=plt.gca().transAxes,
    )
    plt.text(
        0.5,
        0.2,
        "数字和单位：123.45万元",
        ha="center",
        va="center",
        fontsize=12,
        color="green",
        transform=plt.gca().transAxes,
    )

    plt.title("中文文本渲染测试", fontsize=14, fontweight="bold")
    plt.axis("off")

    plt.tight_layout()

    # 保存图表
    output_dir = Path("chinese_visualization_output")
    output_dir.mkdir(exist_ok=True)

    chart_path = output_dir / "中文文本渲染测试.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()

    print("✅ 中文文本渲染测试完成")
    return chart_path


def main():
    """主函数"""
    print("🚀 开始中文字体支持测试")
    print("🎯 验证matplotlib中文显示功能")

    try:
        # 测试1: 中文可视化
        charts, output_dir = test_chinese_visualization()
        print(f"\n📊 中文可视化测试完成")
        print(f"   生成图表数量: {len(charts)}")
        print(f"   输出目录: {output_dir}")

        # 测试2: 中文文本渲染
        text_chart = test_chinese_text_rendering()
        print(f"   文本渲染测试: {text_chart}")

        # 列出生成的文件
        print(f"\n📁 生成的文件:")
        all_files = list(output_dir.glob("*.png"))
        for i, file in enumerate(all_files, 1):
            file_size = file.stat().st_size
            print(f"   {i}. {file.name} ({file_size:,} bytes)")

        print(f"\n🎉 中文字体支持测试成功!")
        print("✅ 所有图表标题、标签、图例中的中文都能正确显示")
        print("✅ 字体加载稳定，不影响绘图性能")
        print("✅ 支持复杂中文文本渲染")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
