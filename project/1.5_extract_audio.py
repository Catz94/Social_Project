"""
Module 1.5 - Extract Audio Clips (Dynamic UI Supported)
Author: Bryan Teh
"""

import os
import json
import subprocess
from pathlib import Path

OFFSETS_FILE = "analysis/offsets.json"
OUTPUT_FOLDER = "audio"
INTERVAL = 3      # 每 3 秒分析一次
DURATION = 2      # 每段 2 秒

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

if os.path.exists(OFFSETS_FILE):
    with open(OFFSETS_FILE, "r", encoding="utf-8") as f:
        offsets_data = json.load(f)
else:
    offsets_data = {
        "camera1": {"path": "videos/camera1.mp4", "target_range": [0, 9999]},
        "camera2": {"path": "videos/camera2.mp4", "target_range": [0, 9999]},
        "camera4": {"path": "videos/camera4.mp4", "target_range": [0, 9999]},
    }

for camera, info in offsets_data.items():
    video_path = info.get("path", "")
    if not os.path.exists(video_path):
        print(f"[Warning] 找不到视频文件，跳过音频提取: {video_path}")
        continue

    out_folder = os.path.join(OUTPUT_FOLDER, camera)
    os.makedirs(out_folder, exist_ok=True)

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ],
        capture_output=True,
        text=True
    )

    try:
        total_duration = int(float(result.stdout.strip()))
    except ValueError:
        total_duration = 0

    target_range = info.get("target_range", [0, total_duration])
    start_sec = max(0, int(target_range[0]))
    end_sec = min(total_duration, int(target_range[1])) if target_range[1] > 0 else total_duration

    for sec in range(start_sec, end_sec, INTERVAL):
        output = os.path.join(out_folder, f"{sec:06d}.wav")
        subprocess.run([
            "ffmpeg",
            "-y",
            "-ss", str(sec),
            "-i", video_path,
            "-t", str(DURATION),
            "-ac", "1",
            "-ar", "16000",
            output
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"[{camera}] Audio extraction completed ({start_sec}s -> {end_sec}s)")