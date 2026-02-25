import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")


def advanced_housing_analysis():
    """EN - EN"""

    print("=== EN ===")

    # 1. EN
    data_path = "test_resources/datasets/Housing.csv"
    df = pd.read_csv(data_path)

    print(f"EN: {df.shape}")

    # 2. EN
    # EN
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

    print(f"EN,EN: {df.shape}")

    # 3. EN
    X = df.drop("price", axis=1)
    y = df["price"]

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
    feature_importance = pd.DataFrame(
        {"feature": X.columns, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)

    print("\n=== EN ===")
    print(f"EN (MAE): {mae:,.0f}")
    print(f"EN (RMSE): {rmse:,.0f}")
    print(f"R² EN: {r2:.3f}")

    print("\n=== EN ===")
    print(feature_importance.head(10))

    # 8. EN
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

    print("\n=== EN ===")
    print(f"ENR²EN: {r2:.3f}")
    print(f"EN: {feature_importance.iloc[0]['feature']}")

    return results


# EN
if __name__ == "__main__":
    results = advanced_housing_analysis()
    print(f"\nEN,EN {len(results)} EN")
