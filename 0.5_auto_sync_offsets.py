"""
Module 0.5 - Automatic Multi-Camera Offset Sync using Audio Cross-Correlation (with Auto Cleanup)
Author: Bryan Teh
"""

import os
import sys
import json
import shutil
import subprocess
import numpy as np
from scipy.signal import fftconvolve

# 获取当前程序所在目录
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# 指定内置的 ffmpeg 路径
ffmpeg_path = os.path.join(base_dir, "ffmpeg", "ffmpeg.exe")

# 修改 subprocess 调用：
# 如果之前写的是 ['ffmpeg', '-i', ...]，现在改成 [ffmpeg_path, '-i', ...]
# 比如：
# cmd = [ffmpeg_path, "-i", main_video_path, ...]
OFFSETS_FILE = "analysis/offsets.json"
CONFIG_FILE = "analysis/config.json"
TEMP_AUDIO_DIR = "analysis/temp_sync_audio"
CLEANUP_FOLDERS = ["analysis", "frames", "audio", "grids"]

SAMPLE_RATE = 16000  # 16kHz 降采样，兼顾计算速度与对齐精度
SYNC_DURATION = 300  # 截取视频前 300 秒(5分钟)音频进行声学特征比对

# ==========================================
# 0. 自动备份配置与清空历史缓存文件夹
# ==========================================
offsets_data = {}
config_data = {}

# 1. 在彻底清空前，将 UI 刚写入的 offsets.json 和 config.json 备份到内存
if os.path.exists(OFFSETS_FILE):
    try:
        with open(OFFSETS_FILE, "r", encoding="utf-8") as f:
            offsets_data = json.load(f)
    except Exception as e:
        print(f"[Warning] 读取 offsets.json 失败: {e}")

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"[Warning] 读取 config.json 失败: {e}")

if not offsets_data:
    print("[Error] 找不到 offsets.json 数据，请先通过 App 界面选择视频文件！")
    exit(1)

# 2. 彻底清理历史缓存文件夹
print("=== 🧹 开始清理历史项目缓存 ===")
for folder in CLEANUP_FOLDERS:
    if os.path.exists(folder):
        try:
            shutil.rmtree(folder)
            print(f"  🗑️ 已彻底清空历史文件夹: {folder}")
        except Exception as e:
            print(f"  ⚠️ 清理 {folder} 时出错: {e}")
    os.makedirs(folder, exist_ok=True)

# 3. 还原 offsets.json 与 config.json 配置文件供后续步骤使用
if offsets_data:
    with open(OFFSETS_FILE, "w", encoding="utf-8") as f:
        json.dump(offsets_data, f, indent=4, ensure_ascii=False)
    print(f"💾 已还原 UI 配置: {OFFSETS_FILE}")

if config_data:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)
    print(f"🔑 已还原 API Key 配置: {CONFIG_FILE}\n")

os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

active_cameras = list(offsets_data.keys())
main_cam = "camera1" if "camera1" in active_cameras else active_cameras[0]

def extract_mono_pcm(video_path, wav_output):
    """使用 ffmpeg 提取单声道 pcm 数据供对齐计算"""
    cmd = [
        "ffmpeg", "-y", "-ss", "0", "-i", video_path,
        "-t", str(SYNC_DURATION),
        "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-f", "s16le", wav_output
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(wav_output):
        return np.fromfile(wav_output, dtype=np.int16).astype(np.float32)
    return None

def calculate_offset(ref_signal, target_signal):
    """利用快速傅里叶互相关算法 (FFT Cross-Correlation) 计算两段音频的时间延迟"""
    if ref_signal is None or target_signal is None:
        return 0.0

    # 归一化信号，去除音量差异影响
    ref_norm = (ref_signal - np.mean(ref_signal)) / (np.std(ref_signal) + 1e-8)
    target_norm = (target_signal - np.mean(target_signal)) / (np.std(target_signal) + 1e-8)

    # 互相关计算
    correlation = fftconvolve(ref_norm, target_norm[::-1], mode="full")
    max_idx = np.argmax(correlation)
    
    # 计算相对于参考音频 (Camera 1) 的偏移秒数
    lag_samples = max_idx - (len(target_norm) - 1)
    offset_seconds = -lag_samples / SAMPLE_RATE
    return round(float(offset_seconds), 2)

print("=" * 60)
print("🎵 正在启动 AI 声学波形互相关对齐算法 (Auto Multi-Cam Alignment)...")
print("=" * 60)

main_video_path = offsets_data[main_cam].get("path", "")
main_pcm_path = os.path.join(TEMP_AUDIO_DIR, f"{main_cam}.pcm")
print(f"提取基准音轨 [{main_cam}]: {main_video_path}")
ref_pcm = extract_mono_pcm(main_video_path, main_pcm_path)

# 基础选取范围（基于 Camera 1 主时间轴）
cam1_range = offsets_data[main_cam].get("target_range", [0, 210])
base_start, base_end = cam1_range[0], cam1_range[1]

for cam, info in offsets_data.items():
    if cam == main_cam:
        offsets_data[cam]["offset"] = 0.0
        offsets_data[cam]["target_range"] = [base_start, base_end]
        continue

    v_path = info.get("path", "")
    if not os.path.exists(v_path):
        continue

    print(f"正在对齐 [{cam}] 声学特征...")
    target_pcm_path = os.path.join(TEMP_AUDIO_DIR, f"{cam}.pcm")
    target_pcm = extract_mono_pcm(v_path, target_pcm_path)

    # 计算该机位相对 Camera 1 的精准延迟秒数
    detected_offset = calculate_offset(ref_pcm, target_pcm)
    
    offsets_data[cam]["offset"] = detected_offset
    offsets_data[cam]["target_range"] = [base_start, base_end]
    print(f"  👉 [{cam}] 识别成功！相对 Camera 1 偏移时间: {detected_offset:+.2f} 秒")

# 保存精准对齐后的配置，供 1.0, 1.5, 3.0 调取
with open(OFFSETS_FILE, "w", encoding="utf-8") as f:
    json.dump(offsets_data, f, indent=4, ensure_ascii=False)

print("\n✅ 所有机位波形对齐完毕！计算出的精准 Offset 已成功保存至 `offsets.json`！")