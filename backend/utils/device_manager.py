#!/usr/bin/env python3
"""
设备管理器 - 自动检测和管理 MPS/GPU/CPU 设备

支持场景:
1. 本地测试: Apple Silicon MPS 加速
2. 生产环境: CUDA GPU + CPU 混合部署
"""

import torch
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """设备类型枚举"""
    MPS = "mps"      # Apple Metal Performance Shaders
    CUDA = "cuda"    # NVIDIA GPU
    CPU = "cpu"      # CPU fallback


class DeviceManager:
    """设备管理器 - 单例模式"""

    _instance: Optional['DeviceManager'] = None
    _device: Optional[torch.device] = None
    _device_type: Optional[DeviceType] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化设备管理器"""
        if self._device is None:
            self._detect_device()

    def _detect_device(self) -> None:
        """
        自动检测最佳设备

        优先级: MPS > CUDA > CPU
        """
        # 1. 检测 Apple MPS (Metal Performance Shaders)
        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            try:
                # 验证 MPS 是否真正可用
                test_tensor = torch.tensor([1.0], device="mps")
                self._device = torch.device("mps")
                self._device_type = DeviceType.MPS
                logger.info("✅ 使用 Apple MPS (Metal) 加速")
                logger.info(f"   - 芯片: Apple Silicon (M1/M2/M3)")
                logger.info(f"   - PyTorch 版本: {torch.__version__}")
                return
            except Exception as e:
                logger.warning(f"⚠️  MPS 检测失败: {e}, 回退到其他设备")

        # 2. 检测 NVIDIA CUDA
        if torch.cuda.is_available():
            self._device = torch.device("cuda")
            self._device_type = DeviceType.CUDA
            cuda_device_count = torch.cuda.device_count()
            cuda_device_name = torch.cuda.get_device_name(0) if cuda_device_count > 0 else "Unknown"
            logger.info("✅ 使用 NVIDIA CUDA GPU 加速")
            logger.info(f"   - GPU 数量: {cuda_device_count}")
            logger.info(f"   - GPU 型号: {cuda_device_name}")
            logger.info(f"   - CUDA 版本: {torch.version.cuda}")
            return

        # 3. 回退到 CPU
        self._device = torch.device("cpu")
        self._device_type = DeviceType.CPU
        logger.warning("⚠️  未检测到 GPU/MPS，使用 CPU")
        logger.warning("   - 性能可能较慢，建议使用 GPU 或 Apple Silicon")

    @property
    def device(self) -> torch.device:
        """获取当前设备"""
        return self._device

    @property
    def device_type(self) -> DeviceType:
        """获取设备类型"""
        return self._device_type

    @property
    def device_name(self) -> str:
        """获取设备名称（用于显示）"""
        if self._device_type == DeviceType.MPS:
            return "Apple MPS (Metal)"
        elif self._device_type == DeviceType.CUDA:
            return f"CUDA GPU ({torch.cuda.get_device_name(0)})"
        else:
            return "CPU"

    def get_sentence_transformer_device(self) -> str:
        """
        获取 sentence-transformers 库的设备字符串

        Returns:
            设备字符串: "mps", "cuda", "cpu"
        """
        return self._device_type.value

    def get_torch_device(self) -> torch.device:
        """
        获取 PyTorch 设备对象

        Returns:
            torch.device 对象
        """
        return self._device

    def optimize_for_inference(self) -> dict:
        """
        根据设备类型返回推理优化配置

        Returns:
            配置字典，包含推理优化参数
        """
        config = {
            "device": self.get_sentence_transformer_device(),
            "show_progress_bar": True,
        }

        if self._device_type == DeviceType.MPS:
            # Apple MPS 优化
            config.update({
                "convert_to_numpy": True,  # MPS 结果转 numpy
                "normalize_embeddings": True,  # 归一化加速余弦相似度计算
            })

        elif self._device_type == DeviceType.CUDA:
            # CUDA GPU 优化
            config.update({
                "convert_to_numpy": True,
                "normalize_embeddings": True,
                "batch_size": 64,  # GPU 可以处理更大的 batch
            })

        else:
            # CPU 优化
            config.update({
                "convert_to_numpy": True,
                "normalize_embeddings": True,
                "batch_size": 16,  # CPU batch size 较小
            })

        return config

    def print_device_info(self) -> None:
        """打印详细的设备信息"""
        print("\n" + "=" * 70)
        print("🖥️  设备检测结果")
        print("=" * 70)
        print(f"  当前设备: {self.device_name}")
        print(f"  设备类型: {self._device_type.value}")
        print(f"  PyTorch 版本: {torch.__version__}")

        if self._device_type == DeviceType.MPS:
            print(f"  MPS 可用: ✅")
            print(f"  MPS 构建: ✅")

        elif self._device_type == DeviceType.CUDA:
            print(f"  CUDA 可用: ✅")
            print(f"  CUDA 版本: {torch.version.cuda}")
            print(f"  GPU 数量: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")

        else:
            print(f"  CPU 核心数: {torch.get_num_threads()}")

        print("=" * 70 + "\n")


# 全局设备管理器实例
device_manager = DeviceManager()


# 便捷函数
def get_device() -> torch.device:
    """获取当前设备"""
    return device_manager.device


def get_device_name() -> str:
    """获取设备名称"""
    return device_manager.device_name


def get_inference_config() -> dict:
    """获取推理优化配置"""
    return device_manager.optimize_for_inference()


if __name__ == "__main__":
    # 测试设备检测
    device_manager.print_device_info()

    # 测试配置
    print("推理优化配置:")
    import json
    print(json.dumps(get_inference_config(), indent=2))
