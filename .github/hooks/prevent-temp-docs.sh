#!/bin/bash
# 阻止临时文档和笔记提交的钩子脚本

# 被禁止的文件名模式
FORBIDDEN_PATTERNS=(
    "notes\.md"
    "thoughts\.md"
    "ideas\.md"
    "draft\.md"
    "scratch\.md"
    "temp\.md"
    "tmp\.md"
    "todo\.md"
    "conversation\.md"
    "chat\.md"
    "summary\.md"
    "analysis\.md"
    "backup\.md"
    "copy\.md"
    "README-COPY\.md"
    "概念.*\.md"
    "设计.*草稿\.md"
    "临时.*\.md"
    "笔记.*\.md"
    ".*笔记\.md"
    ".*草稿\.md"
    ".*临时\.md"
    ".*想法\.md"
)

# 被禁止的内容模式
FORBIDDEN_CONTENT_PATTERNS=(
    "^# .*笔记"
    "^# .*临时"
    "^# .*草稿"
    "^# .*想法"
    "^# .*待办"
    "TODO:.*填充"
    "\[待填充\]"
    "这个文档是临时的"
    "这是一个草稿"
    "临时笔记"
    "思维导图"
    "随手记录"
)

echo "🔍 检查临时文档和笔记..."

for file in "$@"; do
    # 检查文件名模式
    for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
        if echo "$(basename "$file")" | grep -qE "$pattern"; then
            echo "❌ 错误: 检测到被禁止的文档类型: $file"
            echo "文件名模式 '$pattern' 不被允许。"
            echo "请参考 .github/DOCUMENTATION_STANDARDS.md 了解正确的文档命名规范。"
            exit 1
        fi
    done

    # 检查文件内容模式
    if [ -f "$file" ]; then
        for pattern in "${FORBIDDEN_CONTENT_PATTERNS[@]}"; do
            if grep -qE "$pattern" "$file"; then
                echo "❌ 错误: 文档 $file 包含被禁止的内容模式"
                echo "内容模式 '$pattern' 不被允许。"
                echo "请创建符合标准的技术文档，而不是临时笔记或草稿。"
                exit 1
            fi
        done
    fi
done

# 检查是否在允许的目录中
ALLOWED_DIRS=(
    "docs/architecture"
    "docs/implementation"
    "docs/user-guide"
    "docs/api"
    "docs/deployment"
    "docs/testing"
    "docs/maintenance"
)

for file in "$@"; do
    # 跳过 .github 目录下的文件
    if [[ "$file" == .github/* ]]; then
        continue
    fi

    # 检查是否在允许的目录中
    if [[ "$file" == docs/* ]]; then
        is_allowed=false
        for allowed_dir in "${ALLOWED_DIRS[@]}"; do
            if [[ "$file" == "$allowed_dir"* ]]; then
                is_allowed=true
                break
            fi
        done

        if [ "$is_allowed" = false ]; then
            echo "❌ 错误: 文档 $file 不在允许的目录中"
            echo "允许的目录:"
            printf '  %s\n' "${ALLOWED_DIRS[@]}"
            echo "请将文档移动到正确的目录中。"
            exit 1
        fi
    fi
done

echo "✅ 未发现临时文档或违规内容"
exit 0