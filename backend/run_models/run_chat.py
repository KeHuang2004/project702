#!/usr/bin/env python3
"""构建并执行 vllm serve 启动 Chat（问答/生成）模型的脚本。

直接运行：
  python backend/run_models/run_chat.py
会根据 `Config.CHAT_SERVE` 中的 `model_path`, `served_name`, `port`, `gpu_memory_utilization` 构建命令并执行。
"""

import shlex
import subprocess
import sys
import os

# Ensure backend package root is importable when script is run directly
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import Config


def build_command(cfg: dict) -> str:
    model_path = cfg.get("model_path")
    served_name = "chat__model"
    port = cfg.get("port")
    gpu_memory_utilization = cfg.get("gpu_memory_utilization", 0.0)

    if not model_path or not port:
        raise SystemExit("CHAT_SERVE 配置缺少 model_path 或 port")

    parts = [
        "vllm",
        "serve",
        shlex.quote(model_path),
        "--served-model-name",
        shlex.quote(served_name),
        "--port",
        str(port),
    ]
    if gpu_memory_utilization and float(gpu_memory_utilization) > 0.0:
        parts += ["--gpu-memory-utilization", str(float(gpu_memory_utilization))]

    return " ".join(p for p in parts if p)


def main():
    cfg = getattr(Config, "CHAT_SERVE", None)
    if not cfg:
        raise SystemExit("未在 Config 中找到 CHAT_SERVE 配置")

    cmd = build_command(cfg)
    print(cmd)
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(e.returncode)


if __name__ == "__main__":
    main()
