#!/bin/bash

# 数据分析 Docker 镜像构建脚本
# 用于构建 Luncheon AI Flow 的数据分析节点

set -e

echo "=== Luncheon AI Flow 数据分析 Docker 镜像构建 ==="

# 配置变量
IMAGE_NAME="luncheon/code-analysis"
IMAGE_VERSION="1.0"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_VERSION}"
DOCKERFILE_PATH="Dockerfile.data-analysis"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker 是否可用
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装或不在 PATH 中${NC}"
    exit 1
fi

# 检查 Dockerfile 是否存在
if [ ! -f "$DOCKERFILE_PATH" ]; then
    echo -e "${RED}错误: Dockerfile 文件不存在: $DOCKERFILE_PATH${NC}"
    exit 1
fi

# 检查 requirements 文件是否存在
if [ ! -f "requirements-data-analysis.txt" ]; then
    echo -e "${RED}错误: requirements 文件不存在: requirements-data-analysis.txt${NC}"
    exit 1
fi

echo -e "${YELLOW}开始构建 Docker 镜像...${NC}"
echo "镜像名称: $FULL_IMAGE_NAME"
echo "Dockerfile: $DOCKERFILE_PATH"

# 构建镜像
echo -e "${YELLOW}执行 docker build...${NC}"
docker build \
    -f "$DOCKERFILE_PATH" \
    -t "$FULL_IMAGE_NAME" \
    --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --build-arg VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker 镜像构建成功!${NC}"
    echo "镜像名称: $FULL_IMAGE_NAME"

    # 显示镜像信息
    echo -e "${YELLOW}镜像信息:${NC}"
    docker images | grep "$IMAGE_NAME" | head -5

    # 测试镜像
    echo -e "${YELLOW}测试镜像...${NC}"
    docker run --rm "$FULL_IMAGE_NAME" python --version

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 镜像测试成功!${NC}"

        # 验证关键包
        echo -e "${YELLOW}验证关键数据科学包...${NC}"
        docker run --rm "$FULL_IMAGE_NAME" python -c "
import sys
packages = ['pandas', 'numpy', 'matplotlib', 'seaborn', 'sklearn', 'plotly']
missing = []
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg}')
    except ImportError:
        missing.append(pkg)
        print(f'❌ {pkg}')

if missing:
    print(f'缺失包: {missing}')
    sys.exit(1)
else:
    print('所有关键包验证通过!')
"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}🎉 Docker 镜像构建和验证全部完成!${NC}"
            echo
            echo "使用方法:"
            echo "1. 更新 .env 文件中的 DOCKER_IMAGE_NAME=$FULL_IMAGE_NAME"
            echo "2. 重启应用服务"
            echo
            echo "测试命令:"
            echo "docker run --rm -v /path/to/data:/workspace/data $FULL_IMAGE_NAME python your_script.py"
        else
            echo -e "${RED}❌ 包验证失败${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ 镜像测试失败${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Docker 镜像构建失败${NC}"
    exit 1
fi

# 可选：标记为 latest
read -p "是否将镜像标记为 latest? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}标记为 latest...${NC}"
    docker tag "$FULL_IMAGE_NAME" "${IMAGE_NAME}:latest"
    echo -e "${GREEN}✅ 已标记为 ${IMAGE_NAME}:latest${NC}"
fi

echo -e "${GREEN}=== 构建完成 ===${NC}"