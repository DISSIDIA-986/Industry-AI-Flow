#!/usr/bin/env python3
"""
Comprehensive Data Analysis Test Suite
Based on test_cases/data_analysis_code_execution_test_cases.md

Tests data analysis capabilities using actual datasets from test_resources/datasets/:
1. Dataset Loading and Inspection
2. Statistical Analysis
3. Data Transformation and Cleaning
4. Visualization and Charting (validation only - actual rendering requires display)
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

# Add project root to path


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataAnalysisTester:
    """Comprehensive tester for data analysis capabilities"""

    def __init__(self):
        self.test_results = {
            "loading_tests": [],
            "statistical_tests": [],
            "transformation_tests": [],
            "visualization_tests": [],
        }
        self.stats = {"total_tests": 0, "passed": 0, "failed": 0, "errors": 0}
        self.datasets = {}

    def setup(self):
        """Load test datasets"""
        try:
            datasets_dir = Path("test_resources/datasets")

            # Load all CSV datasets
            csv_files = [
                "employee_data.csv",
                "Housing.csv",
                "Thyroid_Diff.csv",
                "Unemployment_Canada_1976_present.csv",
            ]

            for csv_file in csv_files:
                file_path = datasets_dir / csv_file
                if file_path.exists():
                    try:
                        df = pd.read_csv(file_path)
                        dataset_name = csv_file.replace(".csv", "")
                        self.datasets[dataset_name] = df
                        logger.info(
                            f"✅ Loaded {csv_file}: {df.shape[0]} rows, {df.shape[1]} columns"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load {csv_file}: {e}")

            if not self.datasets:
                logger.error("❌ No datasets loaded")
                return False

            logger.info(f"✅ Successfully loaded {len(self.datasets)} datasets")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to setup: {e}")
            import traceback

            traceback.print_exc()
            return False

    # ==================== Category 1: Dataset Loading and Inspection ====================

    def test_1_1_dataset_loading(self):
        """Test Set 1.1: Dataset Loading"""
        logger.info("\n=== Test Set 1.1: Dataset Loading ===")

        for dataset_name, df in self.datasets.items():
            try:
                # Basic loading validation
                has_data = len(df) > 0
                has_columns = len(df.columns) > 0

                passed = has_data and has_columns

                test_result = {
                    "dataset": dataset_name,
                    "rows": len(df),
                    "columns": len(df.columns),
                    "has_data": has_data,
                    "has_columns": has_columns,
                    "passed": passed,
                }

                self.test_results["loading_tests"].append(test_result)
                self.stats["total_tests"] += 1

                if passed:
                    self.stats["passed"] += 1
                    logger.info(
                        f"✅ PASS: {dataset_name} loaded successfully ({len(df)} rows)"
                    )
                else:
                    self.stats["failed"] += 1
                    logger.error(f"❌ FAIL: {dataset_name} - empty or no columns")

            except Exception as e:
                logger.error(f"❌ ERROR: {dataset_name} → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

    def test_1_2_dataset_inspection(self):
        """Test Set 1.2: Dataset Inspection"""
        logger.info("\n=== Test Set 1.2: Dataset Inspection ===")

        for dataset_name, df in self.datasets.items():
            try:
                # Inspect dataset properties
                info = {
                    "shape": df.shape,
                    "columns": list(df.columns),
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "null_counts": df.isnull().sum().to_dict(),
                    "memory_usage": df.memory_usage(deep=True).sum(),
                }

                # Validation: dataset has meaningful structure
                has_multiple_rows = df.shape[0] > 1
                has_multiple_cols = df.shape[1] > 1
                has_varied_types = (
                    len(set(df.dtypes)) > 1 or len(df.dtypes) == 1
                )  # At least consistent types

                passed = has_multiple_rows and has_multiple_cols

                test_result = {
                    "dataset": dataset_name,
                    "info": info,
                    "validation": {
                        "has_multiple_rows": has_multiple_rows,
                        "has_multiple_cols": has_multiple_cols,
                        "has_varied_types": has_varied_types,
                    },
                    "passed": passed,
                }

                self.test_results["loading_tests"].append(test_result)
                self.stats["total_tests"] += 1

                if passed:
                    self.stats["passed"] += 1
                    logger.info(
                        f"✅ PASS: {dataset_name} - Shape: {df.shape}, Types: {len(set(df.dtypes))}"
                    )
                else:
                    self.stats["failed"] += 1
                    logger.error(f"❌ FAIL: {dataset_name} - insufficient structure")

            except Exception as e:
                logger.error(f"❌ ERROR: {dataset_name} → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

    # ==================== Category 2: Statistical Analysis ====================

    def test_2_1_descriptive_statistics(self):
        """Test Set 2.1: Descriptive Statistics"""
        logger.info("\n=== Test Set 2.1: Descriptive Statistics ===")

        for dataset_name, df in self.datasets.items():
            try:
                # Compute descriptive statistics
                numeric_cols = df.select_dtypes(include=[np.number]).columns

                if len(numeric_cols) == 0:
                    logger.warning(f"⚠️ SKIP: {dataset_name} - no numeric columns")
                    continue

                stats = df[numeric_cols].describe()

                # Validate statistics are computed
                has_mean = "mean" in stats.index
                has_std = "std" in stats.index
                has_min_max = "min" in stats.index and "max" in stats.index

                passed = has_mean and has_std and has_min_max

                test_result = {
                    "dataset": dataset_name,
                    "numeric_columns": len(numeric_cols),
                    "statistics": stats.to_dict(),
                    "validation": {
                        "has_mean": has_mean,
                        "has_std": has_std,
                        "has_min_max": has_min_max,
                    },
                    "passed": passed,
                }

                self.test_results["statistical_tests"].append(test_result)
                self.stats["total_tests"] += 1

                if passed:
                    self.stats["passed"] += 1
                    logger.info(
                        f"✅ PASS: {dataset_name} - Statistics computed for {len(numeric_cols)} columns"
                    )
                else:
                    self.stats["failed"] += 1
                    logger.error(f"❌ FAIL: {dataset_name} - incomplete statistics")

            except Exception as e:
                logger.error(f"❌ ERROR: {dataset_name} → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

    def test_2_2_correlation_analysis(self):
        """Test Set 2.2: Correlation Analysis"""
        logger.info("\n=== Test Set 2.2: Correlation Analysis ===")

        for dataset_name, df in self.datasets.items():
            try:
                # Compute correlation matrix
                numeric_cols = df.select_dtypes(include=[np.number]).columns

                if len(numeric_cols) < 2:
                    logger.warning(
                        f"⚠️ SKIP: {dataset_name} - need at least 2 numeric columns"
                    )
                    continue

                corr_matrix = df[numeric_cols].corr()

                # Validate correlation matrix
                is_square = corr_matrix.shape[0] == corr_matrix.shape[1]
                diagonal_is_one = np.allclose(np.diag(corr_matrix), 1.0, atol=0.01)
                is_symmetric = np.allclose(corr_matrix, corr_matrix.T, atol=0.01)

                passed = is_square and diagonal_is_one and is_symmetric

                # Find strong correlations (|r| > 0.7, excluding diagonal)
                strong_corrs = []
                for i in range(len(corr_matrix)):
                    for j in range(i + 1, len(corr_matrix)):
                        corr_value = corr_matrix.iloc[i, j]
                        if abs(corr_value) > 0.7:
                            strong_corrs.append(
                                {
                                    "var1": corr_matrix.index[i],
                                    "var2": corr_matrix.columns[j],
                                    "correlation": float(corr_value),
                                }
                            )

                test_result = {
                    "dataset": dataset_name,
                    "matrix_shape": corr_matrix.shape,
                    "strong_correlations": strong_corrs,
                    "validation": {
                        "is_square": is_square,
                        "diagonal_is_one": diagonal_is_one,
                        "is_symmetric": is_symmetric,
                    },
                    "passed": passed,
                }

                self.test_results["statistical_tests"].append(test_result)
                self.stats["total_tests"] += 1

                if passed:
                    self.stats["passed"] += 1
                    logger.info(
                        f"✅ PASS: {dataset_name} - Correlation matrix {corr_matrix.shape}, {len(strong_corrs)} strong correlations"
                    )
                else:
                    self.stats["failed"] += 1
                    logger.error(f"❌ FAIL: {dataset_name} - invalid correlation matrix")

            except Exception as e:
                logger.error(f"❌ ERROR: {dataset_name} → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

    # ==================== Category 3: Data Transformation ====================

    def test_3_1_missing_data_handling(self):
        """Test Set 3.1: Missing Data Handling"""
        logger.info("\n=== Test Set 3.1: Missing Data Handling ===")

        for dataset_name, df in self.datasets.items():
            try:
                # Check for missing data
                null_counts = df.isnull().sum()
                total_nulls = null_counts.sum()

                # Test different handling strategies
                df_dropna = df.dropna()
                df_fillna = df.fillna(0)  # Simple fill strategy

                # Validate transformations
                dropna_reduced = len(df_dropna) <= len(df)
                fillna_no_nulls = df_fillna.isnull().sum().sum() == 0
                original_preserved = len(df) == len(
                    self.datasets[dataset_name]
                )  # Original unchanged

                passed = dropna_reduced and fillna_no_nulls and original_preserved

                test_result = {
                    "dataset": dataset_name,
                    "original_rows": len(df),
                    "total_nulls": int(total_nulls),
                    "after_dropna": len(df_dropna),
                    "after_fillna_nulls": int(df_fillna.isnull().sum().sum()),
                    "validation": {
                        "dropna_reduced": dropna_reduced,
                        "fillna_no_nulls": fillna_no_nulls,
                        "original_preserved": original_preserved,
                    },
                    "passed": passed,
                }

                self.test_results["transformation_tests"].append(test_result)
                self.stats["total_tests"] += 1

                if passed:
                    self.stats["passed"] += 1
                    logger.info(
                        f"✅ PASS: {dataset_name} - Missing data handling: {total_nulls} nulls, dropna={len(df_dropna)}, fillna=0"
                    )
                else:
                    self.stats["failed"] += 1
                    logger.error(f"❌ FAIL: {dataset_name} - transformation issues")

            except Exception as e:
                logger.error(f"❌ ERROR: {dataset_name} → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

    def test_3_2_data_filtering(self):
        """Test Set 3.2: Data Filtering and Selection"""
        logger.info("\n=== Test Set 3.2: Data Filtering ===")

        for dataset_name, df in self.datasets.items():
            try:
                # Test various filtering operations
                numeric_cols = df.select_dtypes(include=[np.number]).columns

                if len(numeric_cols) == 0:
                    logger.warning(
                        f"⚠️ SKIP: {dataset_name} - no numeric columns for filtering"
                    )
                    continue

                # Filter: rows where first numeric column > median
                first_numeric = numeric_cols[0]
                median_value = df[first_numeric].median()
                df_filtered = df[df[first_numeric] > median_value]

                # Validate filtering
                filter_reduced = (
                    len(df_filtered) < len(df) or len(df_filtered) == 0
                )  # Should reduce or be empty
                filter_correct = (
                    df_filtered[first_numeric].min() >= median_value
                    if len(df_filtered) > 0
                    else True
                )
                original_preserved = len(df) == len(self.datasets[dataset_name])

                passed = filter_reduced and filter_correct and original_preserved

                test_result = {
                    "dataset": dataset_name,
                    "original_rows": len(df),
                    "filter_column": first_numeric,
                    "median_value": float(median_value),
                    "filtered_rows": len(df_filtered),
                    "validation": {
                        "filter_reduced": filter_reduced,
                        "filter_correct": filter_correct,
                        "original_preserved": original_preserved,
                    },
                    "passed": passed,
                }

                self.test_results["transformation_tests"].append(test_result)
                self.stats["total_tests"] += 1

                if passed:
                    self.stats["passed"] += 1
                    logger.info(
                        f"✅ PASS: {dataset_name} - Filtered {len(df)} → {len(df_filtered)} rows"
                    )
                else:
                    self.stats["failed"] += 1
                    logger.error(f"❌ FAIL: {dataset_name} - filtering issues")

            except Exception as e:
                logger.error(f"❌ ERROR: {dataset_name} → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

    # ==================== Category 4: Visualization Validation ====================

    def test_4_1_visualization_data_preparation(self):
        """Test Set 4.1: Visualization Data Preparation"""
        logger.info("\n=== Test Set 4.1: Visualization Data Preparation ===")

        for dataset_name, df in self.datasets.items():
            try:
                numeric_cols = df.select_dtypes(include=[np.number]).columns

                if len(numeric_cols) < 2:
                    logger.warning(
                        f"⚠️ SKIP: {dataset_name} - need at least 2 numeric columns"
                    )
                    continue

                # Prepare data for different chart types
                # 1. Histogram data (single column distribution)
                hist_data = df[numeric_cols[0]].dropna()

                # 2. Scatter plot data (two columns)
                scatter_x = df[numeric_cols[0]].dropna()
                scatter_y = (
                    df[numeric_cols[1]].dropna() if len(numeric_cols) > 1 else scatter_x
                )

                # 3. Box plot data (single column statistics)
                box_stats = df[numeric_cols[0]].describe()

                # Validate data preparation
                hist_ready = len(hist_data) > 0
                scatter_ready = len(scatter_x) > 0 and len(scatter_y) > 0
                box_ready = "min" in box_stats.index and "max" in box_stats.index

                passed = hist_ready and scatter_ready and box_ready

                test_result = {
                    "dataset": dataset_name,
                    "hist_data_points": len(hist_data),
                    "scatter_data_points": min(len(scatter_x), len(scatter_y)),
                    "box_plot_stats": box_stats.to_dict(),
                    "validation": {
                        "hist_ready": hist_ready,
                        "scatter_ready": scatter_ready,
                        "box_ready": box_ready,
                    },
                    "passed": passed,
                }

                self.test_results["visualization_tests"].append(test_result)
                self.stats["total_tests"] += 1

                if passed:
                    self.stats["passed"] += 1
                    logger.info(f"✅ PASS: {dataset_name} - Visualization data prepared")
                else:
                    self.stats["failed"] += 1
                    logger.error(f"❌ FAIL: {dataset_name} - data preparation issues")

            except Exception as e:
                logger.error(f"❌ ERROR: {dataset_name} → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

    def run_all_tests(self):
        """Execute all test categories"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 Starting Comprehensive Data Analysis Tests")
        logger.info("=" * 80)

        if not self.setup():
            logger.error("❌ Setup failed. Cannot proceed with tests.")
            return False

        # Category 1: Loading and Inspection
        logger.info("\n" + "=" * 80)
        logger.info("📂 CATEGORY 1: Dataset Loading and Inspection")
        logger.info("=" * 80)
        self.test_1_1_dataset_loading()
        self.test_1_2_dataset_inspection()

        # Category 2: Statistical Analysis
        logger.info("\n" + "=" * 80)
        logger.info("📊 CATEGORY 2: Statistical Analysis")
        logger.info("=" * 80)
        self.test_2_1_descriptive_statistics()
        self.test_2_2_correlation_analysis()

        # Category 3: Data Transformation
        logger.info("\n" + "=" * 80)
        logger.info("🔄 CATEGORY 3: Data Transformation and Cleaning")
        logger.info("=" * 80)
        self.test_3_1_missing_data_handling()
        self.test_3_2_data_filtering()

        # Category 4: Visualization Data Preparation
        logger.info("\n" + "=" * 80)
        logger.info("📈 CATEGORY 4: Visualization Data Preparation")
        logger.info("=" * 80)
        self.test_4_1_visualization_data_preparation()

        # Print final summary
        self.print_summary()

        return True

    def print_summary(self):
        """Print comprehensive test summary"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 COMPREHENSIVE TEST SUMMARY")
        logger.info("=" * 80)

        total = self.stats["total_tests"]
        passed = self.stats["passed"]
        failed = self.stats["failed"]
        errors = self.stats["errors"]
        pass_rate = (passed / total * 100) if total > 0 else 0

        logger.info(f"\n📈 Overall Results:")
        logger.info(f"   Total Tests: {total}")
        logger.info(f"   Passed: {passed} ({pass_rate:.1f}%)")
        logger.info(f"   Failed: {failed}")
        logger.info(f"   Errors: {errors}")
        logger.info(f"   Datasets Tested: {len(self.datasets)}")

        if pass_rate >= 90:
            logger.info(f"\n✅ EXCELLENT: Pass rate {pass_rate:.1f}% (≥90%)")
        elif pass_rate >= 80:
            logger.info(f"\n✅ GOOD: Pass rate {pass_rate:.1f}% (≥80%)")
        elif pass_rate >= 70:
            logger.info(f"\n⚠️ ACCEPTABLE: Pass rate {pass_rate:.1f}% (≥70%)")
        else:
            logger.info(f"\n❌ NEEDS IMPROVEMENT: Pass rate {pass_rate:.1f}% (<70%)")

        logger.info("\n" + "=" * 80)

    def save_results(
        self, output_file: str = "test_results/data_analysis_results.json"
    ):
        """Save detailed test results to JSON file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Custom JSON encoder for numpy types
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (np.integer, np.int64, np.int32)):
                    return int(obj)
                elif isinstance(obj, (np.floating, np.float64, np.float32)):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, (bool, np.bool_)):
                    return bool(obj)
                elif isinstance(obj, object):
                    # Try to convert to string for other numpy types
                    return str(obj)
                return super(NumpyEncoder, self).default(obj)

        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "statistics": self.stats,
            "datasets_tested": list(self.datasets.keys()),
            "detailed_results": self.test_results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)

        logger.info(f"\n💾 Results saved to: {output_path}")


def main():
    """Main test execution"""
    tester = DataAnalysisTester()
    success = tester.run_all_tests()
    tester.save_results()

    return 0 if success else 1


def test_data_analysis_tester_smoke():
    tester = DataAnalysisTester()
    tester.datasets = {"sample": pd.DataFrame({"x": [1, 2, 3], "y": [3, 4, 5]})}
    tester.test_1_1_dataset_loading()
    assert tester.stats["total_tests"] > 0
    assert tester.stats["passed"] > 0


if __name__ == "__main__":
    sys.exit(main())
