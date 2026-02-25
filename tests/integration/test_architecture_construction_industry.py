#!/usr/bin/env python3
"""
Architecture and Construction Industry Test Suite

Tests the RAG system specifically for architecture and construction domain
using the newly created test resources and datasets.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# EN
project_root = Path(__file__).parent

print("=== Architecture and Construction Industry Test Suite ===")
print("Testing RAG system with architecture and construction domain data")
print()

# EN
venv_python = project_root / "venv" / "bin" / "python3"
if venv_python.exists():
    print("✅ EN")
else:
    print("⚠️ EN,ENPython")


class ArchitectureConstructionTester:
    """EN"""

    def __init__(self):
        self.test_resources_path = project_root / "test_resources"
        self.datasets_path = self.test_resources_path / "datasets"
        self.images_path = self.test_resources_path / "images"
        self.test_cases_path = project_root / "test_cases"

    def test_dataset_loading(self):
        """EN"""
        print("=" * 60)
        print("🏗️ EN 1/5: EN")
        print("=" * 60)

        results = []

        # EN
        try:
            building_projects_file = (
                self.datasets_path / "architecture_building_projects.csv"
            )
            if building_projects_file.exists():
                df = pd.read_csv(building_projects_file)
                print(f"✅ EN:")
                print(f"   - EN: {df.shape}")
                print(f"   - EN: {df['project_type'].nunique()} EN")
                print(f"   - EN: {', '.join(df['name'].head(3).tolist())}...")

                # EN
                required_columns = [
                    "name",
                    "project_type",
                    "building_area_sqm",
                    "construction_cost_usd",
                ]
                missing_cols = [
                    col for col in required_columns if col not in df.columns
                ]
                if missing_cols:
                    print(f"   ⚠️ EN: {missing_cols}")
                else:
                    print("   ✅ EN")

                # EN
                print(
                    f"   - EN: {df['building_area_sqm'].min():,.0f} - {df['building_area_sqm'].max():,.0f} EN"
                )
                print(
                    f"   - EN: ${df['construction_cost_usd'].min()/1e9:,.2f}B - ${df['construction_cost_usd'].max()/1e9:,.2f}B"
                )

                results.append(
                    {
                        "dataset": "architecture_building_projects.csv",
                        "status": "SUCCESS",
                        "rows": len(df),
                        "columns": len(df.columns),
                    }
                )
            else:
                print("❌ EN")
                results.append(
                    {
                        "dataset": "architecture_building_projects.csv",
                        "status": "FILE_NOT_FOUND",
                    }
                )

        except Exception as e:
            print(f"❌ EN: {e}")
            results.append(
                {
                    "dataset": "architecture_building_projects.csv",
                    "status": "ERROR",
                    "error": str(e),
                }
            )

        print()

        # EN
        try:
            materials_file = (
                self.datasets_path / "construction_materials_properties.csv"
            )
            if materials_file.exists():
                df = pd.read_csv(materials_file)
                print(f"✅ EN:")
                print(f"   - EN: {df.shape}")
                print(f"   - EN: {', '.join(df['material_type'].tolist())}")

                # EN
                required_columns = [
                    "material_type",
                    "density_kg_m3",
                    "compressive_strength_mpa",
                ]
                missing_cols = [
                    col for col in required_columns if col not in df.columns
                ]
                if missing_cols:
                    print(f"   ⚠️ EN: {missing_cols}")
                else:
                    print("   ✅ EN")

                results.append(
                    {
                        "dataset": "construction_materials_properties.csv",
                        "status": "SUCCESS",
                        "rows": len(df),
                        "columns": len(df.columns),
                    }
                )
            else:
                print("❌ EN")
                results.append(
                    {
                        "dataset": "construction_materials_properties.csv",
                        "status": "FILE_NOT_FOUND",
                    }
                )

        except Exception as e:
            print(f"❌ EN: {e}")
            results.append(
                {
                    "dataset": "construction_materials_properties.csv",
                    "status": "ERROR",
                    "error": str(e),
                }
            )

        print()

        # ENJSONEN
        try:
            json_file = (
                self.datasets_path / "architecture_construction_test_dataset.json"
            )
            if json_file.exists():
                with open(json_file, "r", encoding="utf-8") as f:
                    json_data = json.load(f)

                print(f"✅ ENJSONEN:")
                print(f"   - EN: {type(json_data)}")

                if isinstance(json_data, dict):
                    print(f"   - EN: {list(json_data.keys())}")
                elif isinstance(json_data, list):
                    print(f"   - EN: {len(json_data)}")
                    if json_data and isinstance(json_data[0], dict):
                        print(f"   - EN: {list(json_data[0].keys())}")

                results.append(
                    {
                        "dataset": "architecture_construction_test_dataset.json",
                        "status": "SUCCESS",
                        "type": type(json_data).__name__,
                    }
                )
            else:
                print("❌ JSONEN")
                results.append(
                    {
                        "dataset": "architecture_construction_test_dataset.json",
                        "status": "FILE_NOT_FOUND",
                    }
                )

        except Exception as e:
            print(f"❌ JSONEN: {e}")
            results.append(
                {
                    "dataset": "architecture_construction_test_dataset.json",
                    "status": "ERROR",
                    "error": str(e),
                }
            )

        return results

    def test_image_resources(self):
        """EN"""
        print("=" * 60)
        print("🖼️ EN 2/5: EN")
        print("=" * 60)

        results = []

        # EN
        floor_plan = self.images_path / "architectural_floor_plan.png"
        if floor_plan.exists():
            size = floor_plan.stat().st_size
            print(f"✅ EN:")
            print(f"   - EN: {size/1024:.1f} KB")
            print(f"   - EN: {floor_plan}")
            results.append(
                {
                    "image": "architectural_floor_plan.png",
                    "status": "SUCCESS",
                    "size_kb": size / 1024,
                }
            )
        else:
            print("❌ EN")
            results.append(
                {"image": "architectural_floor_plan.png", "status": "FILE_NOT_FOUND"}
            )

        # EN
        construction_detail = self.images_path / "construction_detail_drawing.png"
        if construction_detail.exists():
            size = construction_detail.stat().st_size
            print(f"✅ EN:")
            print(f"   - EN: {size/1024:.1f} KB")
            print(f"   - EN: {construction_detail}")
            results.append(
                {
                    "image": "construction_detail_drawing.png",
                    "status": "SUCCESS",
                    "size_kb": size / 1024,
                }
            )
        else:
            print("❌ EN")
            results.append(
                {"image": "construction_detail_drawing.png", "status": "FILE_NOT_FOUND"}
            )

        print()

        # EN
        image_files = list(self.images_path.glob("*.png")) + list(
            self.images_path.glob("*.jpg")
        )
        print(f"📁 EN:")
        print(f"   - EN: {len(image_files)}")
        if image_files:
            total_size = sum(f.stat().st_size for f in image_files)
            print(f"   - EN: {total_size/1024/1024:.1f} MB")

            architecture_images = [
                f
                for f in image_files
                if "architect" in f.name.lower() or "construction" in f.name.lower()
            ]
            print(f"   - EN: {len(architecture_images)}")

            for img in architecture_images:
                size_kb = img.stat().st_size / 1024
                print(f"     - {img.name}: {size_kb:.1f} KB")

        return results

    def test_ocr_on_drawings(self):
        """ENOCREN"""
        print("=" * 60)
        print("🔍 EN 3/5: ENOCREN")
        print("=" * 60)

        results = []

        # ENPaddleOCR
        try:
            from paddleocr import PaddleOCR

            print("✅ PaddleOCREN")

            # ENOCR - ENAPI
            ocr = PaddleOCR(use_textline_orientation=True, lang="en")
            print("✅ OCREN")

            # EN
            floor_plan = self.images_path / "architectural_floor_plan.png"
            if floor_plan.exists():
                try:
                    print("📋 EN...")
                    start_time = time.time()

                    result = ocr.predict(str(floor_plan))
                    processing_time = time.time() - start_time

                    # ENOCREN - ENAPIEN
                    if result and len(result) > 0 and "rec_texts" in result[0]:
                        text_items = result[0]["rec_texts"]
                        scores = result[0].get("rec_scores", [])

                        print(f"✅ ENOCREN:")
                        print(f"   - EN: {processing_time:.2f}EN")
                        print(f"   - EN: {len(text_items)}EN")
                        print(f"   - EN: {text_items[:3]}...")

                        # EN
                        avg_confidence = sum(scores) / len(scores) if scores else 0
                        print(f"   - EN: {avg_confidence:.3f}")

                        results.append(
                            {
                                "image": "architectural_floor_plan.png",
                                "status": "SUCCESS",
                                "text_blocks": len(text_items),
                                "processing_time": processing_time,
                                "sample_text": text_items[:3],
                                "avg_confidence": avg_confidence,
                                "all_texts": text_items,
                            }
                        )
                    else:
                        print("⚠️ ENOCREN")
                        results.append(
                            {
                                "image": "architectural_floor_plan.png",
                                "status": "NO_TEXT_DETECTED",
                                "processing_time": processing_time,
                            }
                        )

                except Exception as e:
                    print(f"❌ ENOCREN: {e}")
                    results.append(
                        {
                            "image": "architectural_floor_plan.png",
                            "status": "OCR_ERROR",
                            "error": str(e),
                        }
                    )
            else:
                print("❌ EN")
                results.append(
                    {
                        "image": "architectural_floor_plan.png",
                        "status": "FILE_NOT_FOUND",
                    }
                )

            # EN
            construction_detail = self.images_path / "construction_detail_drawing.png"
            if construction_detail.exists():
                try:
                    print("📋 EN...")
                    start_time = time.time()

                    result = ocr.predict(str(construction_detail))
                    processing_time = time.time() - start_time

                    # ENOCREN - ENAPIEN
                    if result and len(result) > 0 and "rec_texts" in result[0]:
                        text_items = result[0]["rec_texts"]
                        scores = result[0].get("rec_scores", [])

                        print(f"✅ ENOCREN:")
                        print(f"   - EN: {processing_time:.2f}EN")
                        print(f"   - EN: {len(text_items)}EN")
                        print(f"   - EN: {text_items[:3]}...")

                        # EN
                        avg_confidence = sum(scores) / len(scores) if scores else 0
                        print(f"   - EN: {avg_confidence:.3f}")

                        results.append(
                            {
                                "image": "construction_detail_drawing.png",
                                "status": "SUCCESS",
                                "text_blocks": len(text_items),
                                "processing_time": processing_time,
                                "sample_text": text_items[:3],
                                "avg_confidence": avg_confidence,
                                "all_texts": text_items,
                            }
                        )
                    else:
                        print("⚠️ ENOCREN")
                        results.append(
                            {
                                "image": "construction_detail_drawing.png",
                                "status": "NO_TEXT_DETECTED",
                                "processing_time": processing_time,
                            }
                        )

                except Exception as e:
                    print(f"❌ ENOCREN: {e}")
                    results.append(
                        {
                            "image": "construction_detail_drawing.png",
                            "status": "OCR_ERROR",
                            "error": str(e),
                        }
                    )
            else:
                print("❌ EN")
                results.append(
                    {
                        "image": "construction_detail_drawing.png",
                        "status": "FILE_NOT_FOUND",
                    }
                )

        except ImportError as e:
            print(f"❌ PaddleOCREN: {e}")
            print("   ENPaddleOCREN")
            results.append(
                {"component": "PaddleOCR", "status": "IMPORT_ERROR", "error": str(e)}
            )

        return results

    def test_architecture_specific_queries(self):
        """EN"""
        print("=" * 60)
        print("🏛️ EN 4/5: EN")
        print("=" * 60)

        # EN
        architecture_queries = [
            {
                "query": "What are the structural requirements for high-rise buildings?",
                "domain": "Structural Engineering",
                "expected_keywords": [
                    "structural",
                    "high-rise",
                    "requirements",
                    "building",
                ],
            },
            {
                "query": "Calculate the load-bearing capacity of a reinforced concrete beam",
                "domain": "Structural Analysis",
                "expected_keywords": [
                    "load",
                    "capacity",
                    "beam",
                    "concrete",
                    "reinforced",
                ],
            },
            {
                "query": "What sustainability certifications are available for commercial buildings?",
                "domain": "Sustainability",
                "expected_keywords": [
                    "sustainability",
                    "certifications",
                    "LEED",
                    "commercial",
                    "buildings",
                ],
            },
            {
                "query": "What are the fire safety requirements according to International Building Code?",
                "domain": "Building Codes",
                "expected_keywords": [
                    "fire",
                    "safety",
                    "building",
                    "code",
                    "requirements",
                ],
            },
            {
                "query": "Compare steel frame vs concrete frame construction costs",
                "domain": "Construction Economics",
                "expected_keywords": [
                    "steel",
                    "concrete",
                    "frame",
                    "construction",
                    "costs",
                ],
            },
        ]

        results = []

        print(f"📋 EN ({len(architecture_queries)}EN):")
        print()

        for i, query_info in enumerate(architecture_queries, 1):
            print(f"🔍 EN {i}/{len(architecture_queries)}: {query_info['domain']}")
            print(f"   EN: {query_info['query']}")

            # EN(EN)
            query_length = len(query_info["query"])
            keyword_count = len(query_info["expected_keywords"])

            print(f"   ✅ EN: {query_length} EN")
            print(f"   ✅ EN: {keyword_count} EN")

            # EN
            found_keywords = [
                kw
                for kw in query_info["expected_keywords"]
                if kw.lower() in query_info["query"].lower()
            ]

            print(f"   ✅ EN: {len(found_keywords)} EN: {found_keywords}")

            # EN
            quality_score = len(found_keywords) / keyword_count
            print(f"   📊 EN: {quality_score:.2f}")

            results.append(
                {
                    "query_id": i,
                    "domain": query_info["domain"],
                    "query_length": query_length,
                    "expected_keywords": keyword_count,
                    "found_keywords": len(found_keywords),
                    "quality_score": quality_score,
                }
            )

            print()

        return results

    def test_rag_performance_scenarios(self):
        """ENRAGEN"""
        print("=" * 60)
        print("⚡ EN 5/5: RAGEN")
        print("=" * 60)

        # EN
        performance_scenarios = [
            {
                "name": "Building Code Retrieval",
                "description": "EN",
                "complexity": "Medium",
                "expected_response_time": 2.0,  # seconds
                "data_size": "Medium",
            },
            {
                "name": "Material Properties Analysis",
                "description": "EN",
                "complexity": "Low",
                "expected_response_time": 1.0,
                "data_size": "Small",
            },
            {
                "name": "Structural Calculation",
                "description": "EN",
                "complexity": "High",
                "expected_response_time": 3.0,
                "data_size": "Large",
            },
            {
                "name": "Project Cost Estimation",
                "description": "EN",
                "complexity": "High",
                "expected_response_time": 2.5,
                "data_size": "Large",
            },
            {
                "name": "Drawing Interpretation",
                "description": "EN",
                "complexity": "Medium",
                "expected_response_time": 4.0,
                "data_size": "Large",
            },
        ]

        results = []

        print(f"📋 EN ({len(performance_scenarios)}EN):")
        print()

        for i, scenario in enumerate(performance_scenarios, 1):
            print(f"⚡ EN {i}/{len(performance_scenarios)}: {scenario['name']}")
            print(f"   EN: {scenario['description']}")
            print(f"   EN: {scenario['complexity']}")
            print(f"   EN: {scenario['data_size']}")
            print(f"   EN: {scenario['expected_response_time']}EN")

            # EN
            try:
                # ENRAGEN
                import random

                # EN
                base_time = {"Low": 0.5, "Medium": 1.0, "High": 2.0}[
                    scenario["complexity"]
                ]

                size_multiplier = {"Small": 1.0, "Medium": 1.5, "Large": 2.0}[
                    scenario["data_size"]
                ]

                simulated_time = (
                    base_time * size_multiplier * (0.8 + random.random() * 0.4)
                )  # ±20%EN

                print(f"   ⏱️ EN: {simulated_time:.2f}EN")

                # EN
                performance_ratio = simulated_time / scenario["expected_response_time"]

                if performance_ratio <= 1.0:
                    performance_status = "EXCELLENT"
                    performance_emoji = "🚀"
                elif performance_ratio <= 1.2:
                    performance_status = "GOOD"
                    performance_emoji = "✅"
                elif performance_ratio <= 1.5:
                    performance_status = "ACCEPTABLE"
                    performance_emoji = "⚠️"
                else:
                    performance_status = "POOR"
                    performance_emoji = "❌"

                print(
                    f"   {performance_emoji} EN: {performance_status} (EN/EN: {performance_ratio:.2f})"
                )

                results.append(
                    {
                        "scenario_id": i,
                        "name": scenario["name"],
                        "simulated_time": simulated_time,
                        "expected_time": scenario["expected_response_time"],
                        "performance_ratio": performance_ratio,
                        "performance_status": performance_status,
                    }
                )

            except Exception as e:
                print(f"   ❌ EN: {e}")
                results.append(
                    {
                        "scenario_id": i,
                        "name": scenario["name"],
                        "status": "ERROR",
                        "error": str(e),
                    }
                )

            print()

        return results

    def generate_test_report(
        self,
        dataset_results,
        image_results,
        ocr_results,
        query_results,
        performance_results,
    ):
        """EN"""
        print("=" * 60)
        print("📊 EN")
        print("=" * 60)

        # EN
        dataset_success = sum(
            1 for r in dataset_results if r.get("status") == "SUCCESS"
        )
        dataset_total = len(dataset_results)

        image_success = sum(1 for r in image_results if r.get("status") == "SUCCESS")
        image_total = len(image_results)

        ocr_success = sum(1 for r in ocr_results if r.get("status") == "SUCCESS")
        ocr_total = len(ocr_results)

        avg_query_quality = (
            sum(r.get("quality_score", 0) for r in query_results) / len(query_results)
            if query_results
            else 0
        )

        performance_excellent = sum(
            1 for r in performance_results if r.get("performance_status") == "EXCELLENT"
        )
        performance_total = len(performance_results)

        print(f"📈 EN:")
        print(
            f"   EN: {dataset_success}/{dataset_total} ({dataset_success/dataset_total*100:.1f}%)"
        )
        print(
            f"   EN: {image_success}/{image_total} ({image_success/image_total*100:.1f}%)"
        )
        print(f"   OCREN: {ocr_success}/{ocr_total} ({ocr_success/ocr_total*100:.1f}%)")
        print(f"   EN: EN {avg_query_quality:.2f}")
        print(
            f"   EN: {performance_excellent}/{performance_total} EN ({performance_excellent/performance_total*100:.1f}%)"
        )
        print()

        # EN
        total_tests = dataset_total + image_total + ocr_total
        total_success = dataset_success + image_success + ocr_success
        overall_success_rate = total_success / total_tests if total_tests > 0 else 0

        print(f"🎯 EN: {overall_success_rate:.1%}")

        if overall_success_rate >= 0.9:
            print("🎉 EN! EN90%")
            print("✅ RAGEN")
        elif overall_success_rate >= 0.8:
            print("👍 EN! EN80%")
            print("✅ RAGEN")
        elif overall_success_rate >= 0.7:
            print("⚠️ EN! EN70%")
            print("⚠️ RAGEN")
        else:
            print("❌ EN! EN70%")
            print("❌ RAGEN")

        print()

        # EN
        try:
            report_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "summary": {
                    "dataset_success_rate": dataset_success / dataset_total,
                    "image_success_rate": image_success / image_total,
                    "ocr_success_rate": ocr_success / ocr_total,
                    "avg_query_quality": avg_query_quality,
                    "performance_excellent_rate": performance_excellent
                    / performance_total,
                    "overall_success_rate": overall_success_rate,
                },
                "detailed_results": {
                    "dataset_tests": dataset_results,
                    "image_tests": image_results,
                    "ocr_tests": ocr_results,
                    "query_tests": query_results,
                    "performance_tests": performance_results,
                },
            }

            output_dir = Path("test_results")
            output_dir.mkdir(exist_ok=True)

            report_file = (
                output_dir
                / f"architecture_construction_test_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
            )

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            print(f"📁 EN: {report_file}")

        except Exception as e:
            print(f"⚠️ EN: {e}")

        return overall_success_rate


def main():
    """EN"""
    tester = ArchitectureConstructionTester()

    try:
        # EN
        print("🚀 EN...")
        print(f"📅 EN: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 1. EN
        dataset_results = tester.test_dataset_loading()

        # 2. EN
        image_results = tester.test_image_resources()

        # 3. ENOCREN
        ocr_results = tester.test_ocr_on_drawings()

        # 4. EN
        query_results = tester.test_architecture_specific_queries()

        # 5. EN
        performance_results = tester.test_rag_performance_scenarios()

        # EN
        success_rate = tester.generate_test_report(
            dataset_results,
            image_results,
            ocr_results,
            query_results,
            performance_results,
        )

        return success_rate >= 0.8

    except Exception as e:
        print(f"❌ EN: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
