import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")


def advanced_housing_analysis():
    """高级房价分析 - 机器学习建模"""

    print("=== 高级房价分析开始 ===")

    # 1. 数据预处理
    data_path = "/Users/niuyp/Documents/github.com/Industry-AI-Flow/test_resources/datasets/Housing.csv"
    df = pd.read_csv(data_path)

    print(f"原始数据形状: {df.shape}")

    # 2. 特征工程
    # 处理分类变量
    categorical_cols = [
        "mainroad",
        "guestroom",
        "basement",
        "hotwaterheating",
        "airconditioning",
        "prefarea",
        "furnishingstatus",
    ]

    le = LabelEncoder()
    for col in categorical_cols:
        df[col] = le.fit_transform(df[col])

    print(f"特征工程完成，处理后形状: {df.shape}")

    # 3. 准备数据
    X = df.drop("price", axis=1)
    y = df["price"]

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
    feature_importance = pd.DataFrame(
        {"feature": X.columns, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)

    print("\n=== 模型评估结果 ===")
    print(f"平均绝对误差 (MAE): {mae:,.0f}")
    print(f"均方根误差 (RMSE): {rmse:,.0f}")
    print(f"R² 分数: {r2:.3f}")

    print("\n=== 特征重要性排名 ===")
    print(feature_importance.head(10))

    # 8. 创建结果摘要
    results = {
        "model_performance": {
            "mae": float(mae),
            "mse": float(mse),
            "rmse": float(rmse),
            "r2_score": float(r2),
        },
        "feature_importance": feature_importance.set_index("feature")[
            "importance"
        ].to_dict(),
        "data_shape": {
            "original": df.shape,
            "features": X.shape,
            "train_size": len(X_train),
            "test_size": len(X_test),
        },
    }

    print("\n=== 高级分析完成 ===")
    print(f"模型R²分数: {r2:.3f}")
    print(f"最重要的特征: {feature_importance.iloc[0]['feature']}")

    return results


# 执行高级分析
if __name__ == "__main__":
    results = advanced_housing_analysis()
    print(f"\n高级分析完成，生成了 {len(results)} 个主要指标")
