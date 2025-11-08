#!/usr/bin/env python3
"""
Docker环境中文字体支持测试脚本
"""

import sys
import os
sys.path.insert(0, '/app/utils')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

print("🚀 开始Docker环境中文字体支持测试")

# 测试中文字体支持
try:
    import matplotlib_chinese_support
    success = matplotlib_chinese_support.setup_chinese_matplotlib()
    if success:
        print("✅ 中文字体支持模块加载成功")
    else:
        print("⚠️ 中文字体支持模块加载失败")
except Exception as e:
    print(f"⚠️ 中文字体支持模块加载失败: {e}")
    # 使用备用方案
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'WenQuanYi Micro Hei', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    print("✅ 使用备用中文字体配置")

# 创建简单的中文测试图表
print("📊 生成中文测试图表...")
plt.figure(figsize=(10, 6))
x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.plot(x, y, label='正弦函数', linewidth=2)
plt.title('Docker环境中文显示测试', fontsize=16, fontweight='bold')
plt.xlabel('X轴（弧度）', fontsize=12)
plt.ylabel('Y轴值', fontsize=12)
plt.legend()
plt.grid(True, alpha=0.3)

# 保存图表
output_path = '/workspace/output/docker中文测试图.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()

print(f"✅ Docker环境中文测试图已生成: {output_path}")

# 验证文件存在
if os.path.exists(output_path):
    file_size = os.path.getsize(output_path)
    print(f"📁 文件大小: {file_size:,} bytes")
    print("🎉 Docker环境中文字体支持测试完成！")
else:
    print("❌ 图表文件生成失败")