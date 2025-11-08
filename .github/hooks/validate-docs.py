#!/usr/bin/env python3
"""
文档内容质量验证脚本
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional

class DocumentValidator:
    def __init__(self, docs_path: str = "docs"):
        self.docs_path = Path(docs_path)
        self.errors = []
        self.warnings = []

    def validate_all(self) -> bool:
        """验证所有文档"""
        md_files = list(self.docs_path.rglob("*.md"))

        for file_path in md_files:
            self.validate_single(file_path)

        self.print_results()
        return len(self.errors) == 0

    def validate_single(self, file_path: Path) -> None:
        """验证单个文档"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查文档结构
            self.check_document_structure(file_path, content)

            # 检查内容质量
            self.check_content_quality(file_path, content)

        except Exception as e:
            self.errors.append(f"文件 {file_path}: 无法读取 - {e}")

    def check_document_structure(self, file_path: Path, content: str) -> None:
        """检查文档结构"""
        lines = content.split('\n')

        # 检查是否有标题
        has_title = any(line.strip().startswith('#') for line in lines)
        if not has_title:
            self.errors.append(f"{file_path}: 缺少文档标题")

        # 检查是否描述
        has_description = any("## 概述" in line or "## 简介" in line for line in lines)
        if not has_description:
            self.warnings.append(f"{file_path}: 建议添加概述部分")

    def check_content_quality(self, file_path: Path, content: str) -> None:
        """检查内容质量"""
        # 检查是否包含模板或占位符
        if "TODO:" in content or "[待填充]" in content:
            self.errors.append(f"{file_path}: 包含未完成的内容标记")

        # 检查内容长度
        if len(content.strip()) < 500:
            self.errors.append(f"{file_path}: 内容过于简短 (少于500字符)")

        # 检查是否有实际价值
        if not self.has_substantial_content(content):
            self.errors.append(f"{file_path}: 缺乏实质性的技术内容")

    def has_substantial_content(self, content: str) -> bool:
        """检查是否有实质性内容"""
        # 检查是否包含技术性内容
        technical_patterns = [
            r'```',  # 代码块
            r'!\[.*\]',  # 图片
            r'https?://',  # 链接
            r'## 功能|## 接口|## 方法', # 章节标题
            r'CREATE TABLE|SELECT \*',  # SQL
            r'function\s+\w+\s*\(',  # 函数定义
            r'class\s+\w+\s*:',  # 类定义
        ]

        return any(re.search(pattern, content, re.IGNORECASE) for pattern in technical_patterns)

    def print_results(self) -> None:
        """打印验证结果"""
        if self.errors:
            print("\n❌ 文档验证失败:")
            for error in self.errors:
                print(f"  - {error}")
            print(f"\n发现 {len(self.errors)} 个错误，请修复后重新提交")
            exit(1)

        if self.warnings:
            print("\n⚠️ 文档建议:")
            for warning in self.warnings:
                print(f"  - {warning}")

        print("\n✅ 文档验证通过")

if __name__ == "__main__":
    validator = DocumentValidator()
    success = validator.validate_all()
    exit(0 if success else 1)