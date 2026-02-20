#!/usr/bin/env python3
"""
Industry AI Flow - 自动化Code Review脚本
按照CODE_REVIEW_STRATEGY.md执行完整评审
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class CodeReviewRunner:
    """Code Review执行器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backend_dir = project_root / "backend"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "phase1_quick_diagnosis": {},
            "phase2_deep_review": {},
            "phase3_runtime_validation": {},
            "issues": [],
            "summary": {}
        }
        
    def run_command(self, cmd: List[str], cwd: Path = None) -> Tuple[int, str, str]:
        """执行命令并返回结果"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    # ========== Phase 1: 快速诊断 ==========
    
    def phase1_document_scan(self) -> Dict[str, Any]:
        """文档与架构快速扫描"""
        print("\n📋 [Phase 1.1] 文档与架构快速扫描...")
        
        docs_to_check = [
            "README.md",
            "ARCHITECTURE.md",
            "docs/ARCHITECTURE.md",
            "docs/ARCHITECTURE_DIAGRAM.html",
            "docs/reports/CAPSTONE_VALIDATION_TEST_PLAN.md",
            "CODE_REVIEW_STRATEGY.md"
        ]
        
        results = {
            "total": len(docs_to_check),
            "exists": 0,
            "missing": [],
            "found": []
        }
        
        for doc in docs_to_check:
            doc_path = self.project_root / doc
            if doc_path.exists():
                results["exists"] += 1
                results["found"].append(doc)
                # 检查文档大小
                size = doc_path.stat().st_size
                print(f"  ✅ {doc} ({size} bytes)")
            else:
                results["missing"].append(doc)
                print(f"  ❌ {doc} - 缺失")
        
        score = (results["exists"] / results["total"]) * 100
        print(f"\n📊 文档完整性: {score:.0f}%")
        
        results["score"] = score
        return results
    
    def phase1_code_structure_review(self) -> Dict[str, Any]:
        """代码结构快速审查"""
        print("\n🏗️  [Phase 1.2] 代码结构快速审查...")
        
        results = {
            "directories": [],
            "modules": [],
            "issues": [],
            "score": 0
        }
        
        # 检查关键目录
        key_dirs = [
            "api",
            "services",
            "agents",
            "tools",
            "security",
            "middleware",
            "observability"
        ]
        
        for dir_name in key_dirs:
            dir_path = f"backend/{dir_name}"
            full_path = self.backend_dir / dir_name
            if full_path.exists() and full_path.is_dir():
                # 统计Python文件数量
                py_files = list(full_path.glob("**/*.py"))
                results["directories"].append({
                    "path": dir_path,
                    "file_count": len(py_files)
                })
                print(f"  ✅ {dir_path} ({len(py_files)} files)")
            else:
                results["issues"].append(f"Missing directory: {dir_path}")
                print(f"  ❌ {dir_path} - 缺失")
        
        # 检查__init__.py文件
        init_files = list(self.backend_dir.glob("**/__init__.py"))
        results["init_files"] = len(init_files)
        print(f"  📦 __init__.py文件: {len(init_files)}")
        
        # 计算结构评分
        score = min(100, (len(results["directories"]) / len(key_dirs)) * 100)
        results["score"] = score
        
        return results
    
    def phase1_ai_ml_modules_review(self) -> Dict[str, Any]:
        """AI/ML核心模块快速审查"""
        print("\n🤖 [Phase 1.3] AI/ML核心模块快速审查...")
        
        results = {
            "rag_system": {},
            "cost_estimation": {},
            "code_generation": {},
            "llm_integration": {},
            "score": 0
        }
        
        # RAG系统检查
        rag_modules = [
            "backend/services/core/embedder.py",
            "backend/services/core/vectorstore.py",
            "backend/services/core/chunker.py",
            "backend/services/retrieval/hybrid_search.py",
            "backend/services/retrieval/reranker.py"
        ]
        
        rag_found = 0
        for module in rag_modules:
            if (self.project_root / module).exists():
                rag_found += 1
                print(f"  ✅ RAG: {module}")
            else:
                print(f"  ❌ RAG: {module} - 缺失")
        
        results["rag_system"] = {
            "total": len(rag_modules),
            "found": rag_found,
            "score": (rag_found / len(rag_modules)) * 100
        }
        
        # 成本估算检查
        cost_modules = [
            "backend/api/cost_estimation_routes.py",
            "backend/services/cost_estimation_service.py",
            "backend/services/llm_integration/cost_tracker.py"
        ]
        
        cost_found = 0
        for module in cost_modules:
            if (self.project_root / module).exists():
                cost_found += 1
                print(f"  ✅ 成本估算: {module}")
            else:
                print(f"  ❌ 成本估算: {module} - 缺失")
        
        results["cost_estimation"] = {
            "total": len(cost_modules),
            "found": cost_found,
            "score": (cost_found / len(cost_modules)) * 100
        }
        
        # 代码生成检查
        codegen_modules = [
            "backend/services/data_analysis/data_analysis_agent.py",
            "backend/services/code_executor.py",
            "backend/agents/code_analysis_agent.py",
            "backend/agents/code_execution_agent.py"
        ]
        
        codegen_found = 0
        for module in codegen_modules:
            if (self.project_root / module).exists():
                codegen_found += 1
                print(f"  ✅ 代码生成: {module}")
            else:
                print(f"  ❌ 代码生成: {module} - 缺失")
        
        results["code_generation"] = {
            "total": len(codegen_modules),
            "found": codegen_found,
            "score": (codegen_found / len(codegen_modules)) * 100
        }
        
        # LLM集成检查
        llm_modules = [
            "backend/services/llm_integration/dispatch_service.py",
            "backend/services/llm_integration/llm_client.py",
            "backend/api/llm_dispatch_routes.py"
        ]
        
        llm_found = 0
        for module in llm_modules:
            if (self.project_root / module).exists():
                llm_found += 1
                print(f"  ✅ LLM集成: {module}")
            else:
                print(f"  ❌ LLM集成: {module} - 缺失")
        
        results["llm_integration"] = {
            "total": len(llm_modules),
            "found": llm_found,
            "score": (llm_found / len(llm_modules)) * 100
        }
        
        # 计算总体评分
        avg_score = (
            results["rag_system"]["score"] +
            results["cost_estimation"]["score"] +
            results["code_generation"]["score"] +
            results["llm_integration"]["score"]
        ) / 4
        
        results["score"] = avg_score
        print(f"\n📊 AI/ML模块完整性: {avg_score:.0f}%")
        
        return results
    
    def phase1_key_code_review(self) -> Dict[str, Any]:
        """关键代码片段深度审查"""
        print("\n🔍 [Phase 1.4] 关键代码片段深度审查...")
        
        # 选择关键模块进行审查
        key_modules = [
            "backend/services/retrieval/hybrid_search.py",
            "backend/services/llm_integration/dispatch_service.py",
            "backend/services/cost_estimation_service.py",
            "backend/services/code_executor.py"
        ]
        
        results = {
            "modules_reviewed": 0,
            "total_lines": 0,
            "total_functions": 0,
            "issues": []
        }
        
        for module_path in key_modules:
            full_path = self.project_root / module_path
            if not full_path.exists():
                results["issues"].append(f"Missing key module: {module_path}")
                continue
            
            # 读取文件
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    results["modules_reviewed"] += 1
                    results["total_lines"] += len(lines)
                    
                    # 统计函数数量
                    import ast
                    try:
                        tree = ast.parse(content)
                        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                        results["total_functions"] += len(functions)
                    except:
                        pass
                    
                    print(f"  ✅ {module_path}")
                    print(f"     - Lines: {len(lines)}")
                    print(f"     - Functions: {len(functions) if 'functions' in locals() else 'N/A'}")
                    
            except Exception as e:
                results["issues"].append(f"Error reading {module_path}: {e}")
                print(f"  ❌ {module_path}: {e}")
        
        return results
    
    def phase1_dependency_check(self) -> Dict[str, Any]:
        """依赖与配置检查"""
        print("\n📦 [Phase 1.5] 依赖与配置检查...")
        
        results = {
            "requirements_files": [],
            "dependencies": [],
            "issues": [],
            "score": 0
        }
        
        # 检查requirements文件
        req_files = [
            "requirements.txt",
            "requirements/base.txt",
            "requirements/lock/py313-capstone.txt"
        ]
        
        for req_file in req_files:
            full_path = self.project_root / req_file
            if full_path.exists():
                # 统计依赖数量
                with open(full_path, 'r') as f:
                    deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    results["requirements_files"].append({
                        "path": req_file,
                        "dependency_count": len(deps)
                    })
                    print(f"  ✅ {req_file} ({len(deps)} dependencies)")
            else:
                results["issues"].append(f"Missing requirements file: {req_file}")
                print(f"  ❌ {req_file} - 缺失")
        
        # 检查配置文件
        config_files = [
            "backend/config.py",
            ".env.example",
            ".gitignore"
        ]
        
        for config_file in config_files:
            full_path = self.project_root / config_file
            if full_path.exists():
                print(f"  ✅ {config_file}")
            else:
                results["issues"].append(f"Missing config file: {config_file}")
                print(f"  ❌ {config_file} - 缺失")
        
        # 计算评分
        score = min(100, (len(results["requirements_files"]) / len(req_files)) * 100)
        results["score"] = score
        
        return results
    
    # ========== Phase 2: 深度评审 ==========
    
    def phase2_architecture_review(self) -> Dict[str, Any]:
        """架构设计深度评审"""
        print("\n🏛️  [Phase 2.1] 架构设计深度评审...")
        
        results = {
            "layers": {},
            "patterns": [],
            "issues": [],
            "score": 0
        }
        
        # 检查分层架构
        layers = {
            "API层": "api",
            "服务层": "services",
            "智能体层": "agents",
            "工具层": "tools",
            "中间件层": "middleware",
            "安全层": "security"
        }
        
        for layer_name, dir_name in layers.items():
            layer_path = f"backend/{dir_name}"
            full_path = self.backend_dir / dir_name
            if full_path.exists() and full_path.is_dir():
                py_files = list(full_path.glob("**/*.py"))
                results["layers"][layer_name] = {
                    "path": layer_path,
                    "file_count": len(py_files),
                    "exists": True
                }
                print(f"  ✅ {layer_name}: {layer_path} ({len(py_files)} files)")
            else:
                results["issues"].append(f"Missing layer: {layer_name} ({layer_path})")
                print(f"  ❌ {layer_name}: {layer_path} - 缺失")
        
        # 检查架构模式
        patterns_found = []
        
        # 检查是否有依赖注入
        if (self.backend_dir / "security" / "dependencies.py").exists():
            patterns_found.append("依赖注入 (DI)")
        
        # 检查是否有中间件
        middleware_files = list((self.backend_dir / "middleware").glob("*.py"))
        if len(middleware_files) > 0:
            patterns_found.append("中间件模式 (Middleware)")
        
        # 检查是否有工作流
        if (self.backend_dir / "services" / "workflows").exists():
            patterns_found.append("工作流模式 (Workflow)")
        
        results["patterns"] = patterns_found
        
        for pattern in patterns_found:
            print(f"  ✓ {pattern}")
        
        # 计算评分
        score = min(100, (len(results["layers"]) / len(layers)) * 100)
        results["score"] = score
        print(f"\n📊 架构设计评分: {score:.0f}%")
        
        return results
    
    def phase2_ai_ml_engineering_review(self) -> Dict[str, Any]:
        """AI/ML工程深度评审"""
        print("\n🧠 [Phase 2.2] AI/ML工程深度评审...")
        
        results = {
            "rag_analysis": {},
            "llm_integration": {},
            "cost_estimation": {},
            "code_generation": {},
            "score": 0
        }
        
        # RAG系统深度分析
        print("\n  🔍 RAG系统深度分析:")
        rag_checklist = {
            "嵌入模型": "backend/services/core/embedder.py",
            "向量数据库": "backend/services/core/vectorstore.py",
            "文档分块": "backend/services/core/chunker.py",
            "混合检索": "backend/services/retrieval/hybrid_search.py",
            "重排序": "backend/services/retrieval/reranker.py"
        }
        
        rag_score = 0
        for component, path in rag_checklist.items():
            if (self.project_root / path).exists():
                rag_score += 20
                print(f"    ✅ {component}: 存在")
            else:
                print(f"    ❌ {component}: 缺失")
        
        results["rag_analysis"]["score"] = rag_score
        
        # LLM集成深度分析
        print("\n  🔍 LLM集成深度分析:")
        llm_checklist = {
            "多LLM提供商": "backend/services/llm_integration/types.py",
            "调度服务": "backend/services/llm_integration/dispatch_service.py",
            "成本追踪": "backend/services/llm_integration/cost_tracker.py"
        }
        
        llm_score = 0
        for component, path in llm_checklist.items():
            if (self.project_root / path).exists():
                llm_score += 33
                print(f"    ✅ {component}: 存在")
            else:
                print(f"    ❌ {component}: 缺失")
        
        results["llm_integration"]["score"] = llm_score
        
        # 成本估算深度分析
        print("\n  🔍 成本估算深度分析:")
        cost_checklist = {
            "成本估算服务": "backend/services/cost_estimation_service.py",
            "成本API": "backend/api/cost_estimation_routes.py",
            "成本追踪": "backend/services/llm_integration/cost_tracker.py"
        }
        
        cost_score = 0
        for component, path in cost_checklist.items():
            if (self.project_root / path).exists():
                cost_score += 33
                print(f"    ✅ {component}: 存在")
            else:
                print(f"    ❌ {component}: 缺失")
        
        results["cost_estimation"]["score"] = cost_score
        
        # 代码生成深度分析
        print("\n  🔍 代码生成深度分析:")
        codegen_checklist = {
            "数据分析Agent": "backend/services/data_analysis/data_analysis_agent.py",
            "代码执行器": "backend/services/code_executor.py",
            "Docker执行": "backend/services/code_executor/docker_executor.py",
            "代码验证": "backend/services/code_executor/validator.py"
        }
        
        codegen_score = 0
        for component, path in codegen_checklist.items():
            if (self.project_root / path).exists():
                codegen_score += 25
                print(f"    ✅ {component}: 存在")
            else:
                print(f"    ❌ {component}: 缺失")
        
        results["code_generation"]["score"] = codegen_score
        
        # 计算总体评分
        avg_score = (
            results["rag_analysis"]["score"] +
            results["llm_integration"]["score"] +
            results["cost_estimation"]["score"] +
            results["code_generation"]["score"]
        ) / 4
        
        results["score"] = avg_score
        print(f"\n📊 AI/ML工程评分: {avg_score:.0f}%")
        
        return results
    
    def phase2_code_quality_review(self) -> Dict[str, Any]:
        """代码质量深度评审"""
        print("\n📝 [Phase 2.3] 代码质量深度评审...")
        
        results = {
            "pylint": None,
            "mypy": None,
            "test_coverage": None,
            "score": 0
        }
        
        # 检查是否安装了pylint
        print("\n  🔍 代码质量检查工具:")
        tools = ["pylint", "mypy", "pytest"]
        installed_tools = []
        
        for tool in tools:
            rc, stdout, stderr = self.run_command([tool, "--version"], cwd=self.backend_dir)
            if rc == 0:
                installed_tools.append(tool)
                version = stdout.split('\n')[0]
                print(f"    ✅ {tool}: {version}")
            else:
                print(f"    ❌ {tool}: 未安装")
        
        results["installed_tools"] = installed_tools
        
        # 检查测试文件
        print("\n  🔍 测试覆盖:")
        test_dirs = [
            "tests/unit",
            "tests/integration",
            "tests/e2e"
        ]
        
        total_tests = 0
        for test_dir in test_dirs:
            full_path = self.project_root / test_dir
            if full_path.exists():
                test_files = list(full_path.glob("**/test_*.py"))
                total_tests += len(test_files)
                print(f"    ✅ {test_dir}: {len(test_files)} test files")
            else:
                print(f"    ❌ {test_dir}: 缺失")
        
        results["test_files"] = total_tests
        
        # 计算评分
        score = 0
        if len(installed_tools) >= 2:
            score += 30
        if total_tests >= 10:
            score += 40
        if total_tests >= 20:
            score += 30
        
        results["score"] = score
        print(f"\n📊 代码质量评分: {score}/100")
        
        return results
    
    def phase2_security_review(self) -> Dict[str, Any]:
        """安全性深度评审"""
        print("\n🔒 [Phase 2.4] 安全性深度评审...")
        
        results = {
            "auth": {},
            "security_checks": [],
            "issues": [],
            "score": 0
        }
        
        # 检查身份认证
        print("\n  🔍 身份认证与授权:")
        auth_files = {
            "身份认证": "backend/security/auth.py",
            "上下文管理": "backend/security/context.py",
            "依赖检查": "backend/security/dependencies.py",
            "速率限制": "backend/security/rate_limiter.py",
            "密钥管理": "backend/security/secret_manager.py"
        }
        
        auth_score = 0
        for component, path in auth_files.items():
            if (self.project_root / path).exists():
                auth_score += 20
                print(f"    ✅ {component}: 存在")
            else:
                print(f"    ❌ {component}: 缺失")
        
        results["auth"]["score"] = auth_score
        
        # 检查安全服务
        print("\n  🔍 安全服务:")
        security_services = {
            "数据脱敏": "backend/services/security/redaction_service.py",
            "上传保护": "backend/services/security/upload_guard.py",
            "出口保护": "backend/services/security/egress_guard.py",
            "安全检查": "backend/safety/groundedness_checker.py"
        }
        
        security_score = 0
        for service, path in security_services.items():
            if (self.project_root / path).exists():
                security_score += 25
                print(f"    ✅ {service}: 存在")
            else:
                print(f"    ❌ {service}: 缺失")
        
        results["security_checks"].append({"name": "安全服务", "score": security_score})
        
        # 计算总体评分
        avg_score = (results["auth"]["score"] + security_score) / 2
        results["score"] = avg_score
        print(f"\n📊 安全性评分: {avg_score:.0f}%")
        
        return results
    
    # ========== 运行所有阶段 ==========
    
    def run_all_phases(self):
        """运行所有评审阶段"""
        print("\n" + "="*60)
        print("🚀 Industry AI Flow - Code Review开始执行")
        print("="*60)
        
        # Phase 1: 快速诊断
        print("\n" + "="*60)
        print("📋 Phase 1: 快速诊断（Quick Diagnosis）")
        print("="*60)
        
        self.results["phase1_quick_diagnosis"]["document_scan"] = self.phase1_document_scan()
        self.results["phase1_quick_diagnosis"]["code_structure"] = self.phase1_code_structure_review()
        self.results["phase1_quick_diagnosis"]["ai_ml_modules"] = self.phase1_ai_ml_modules_review()
        self.results["phase1_quick_diagnosis"]["key_code_review"] = self.phase1_key_code_review()
        self.results["phase1_quick_diagnosis"]["dependency_check"] = self.phase1_dependency_check()
        
        # Phase 2: 深度评审
        print("\n" + "="*60)
        print("🔍 Phase 2: 深度评审（Deep Review）")
        print("="*60)
        
        self.results["phase2_deep_review"]["architecture"] = self.phase2_architecture_review()
        self.results["phase2_deep_review"]["ai_ml_engineering"] = self.phase2_ai_ml_engineering_review()
        self.results["phase2_deep_review"]["code_quality"] = self.phase2_code_quality_review()
        self.results["phase2_deep_review"]["security"] = self.phase2_security_review()
        
        # 生成总结
        self.generate_summary()
        
        # 保存结果
        self.save_results()
        
        # 打印最终总结
        self.print_final_summary()
    
    def generate_summary(self):
        """生成总结"""
        # 计算总体评分
        phase1_scores = [
            self.results["phase1_quick_diagnosis"]["document_scan"]["score"],
            self.results["phase1_quick_diagnosis"]["code_structure"]["score"],
            self.results["phase1_quick_diagnosis"]["ai_ml_modules"]["score"]
        ]
        
        phase2_scores = [
            self.results["phase2_deep_review"]["architecture"]["score"],
            self.results["phase2_deep_review"]["ai_ml_engineering"]["score"],
            self.results["phase2_deep_review"]["code_quality"]["score"],
            self.results["phase2_deep_review"]["security"]["score"]
        ]
        
        phase1_avg = sum(phase1_scores) / len(phase1_scores)
        phase2_avg = sum(phase2_scores) / len(phase2_scores)
        overall_avg = (phase1_avg + phase2_avg) / 2
        
        self.results["summary"] = {
            "phase1_average": phase1_avg,
            "phase2_average": phase2_avg,
            "overall_score": overall_avg,
            "grade": self.calculate_grade(overall_avg),
            "recommendation": self.get_recommendation(overall_avg)
        }
    
    def calculate_grade(self, score: float) -> str:
        """计算等级"""
        if score >= 90:
            return "A (优秀)"
        elif score >= 80:
            return "B (良好)"
        elif score >= 70:
            return "C (及格)"
        elif score >= 60:
            return "D (不及格)"
        else:
            return "F (失败)"
    
    def get_recommendation(self, score: float) -> str:
        """获取建议"""
        if score >= 80:
            return "系统质量良好，建议持续改进和优化"
        elif score >= 70:
            return "系统基本可用，建议修复中等问题"
        elif score >= 60:
            return "系统存在明显问题，需要紧急修复关键问题"
        else:
            return "系统质量不达标，需要全面重构"
    
    def save_results(self):
        """保存结果"""
        output_file = self.project_root / "CODE_REVIEW_RESULTS.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 结果已保存到: {output_file}")
    
    def print_final_summary(self):
        """打印最终总结"""
        print("\n" + "="*60)
        print("📊 Code Review最终总结")
        print("="*60)
        
        summary = self.results["summary"]
        
        print(f"\n🎯 总体评分: {summary['overall_score']:.1f}/100")
        print(f"📈 等级: {summary['grade']}")
        print(f"💡 建议: {summary['recommendation']}")
        
        print(f"\n📋 Phase 1 平均分: {summary['phase1_average']:.1f}/100")
        print(f"📋 Phase 2 平均分: {summary['phase2_average']:.1f}/100")
        
        print("\n✅ 评审完成！")


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent.parent
    runner = CodeReviewRunner(project_root)
    runner.run_all_phases()


if __name__ == "__main__":
    main()
