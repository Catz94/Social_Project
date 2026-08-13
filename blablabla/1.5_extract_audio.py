import os
import subprocess
from pathlib import Path

VIDEO_FOLDER = "videos"
OUTPUT_FOLDER = "audio"

INTERVAL = 3      # 每 3 秒分析一次
DURATION = 2      # 每段 2 秒

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

for video in os.listdir(VIDEO_FOLDER):

    if not video.endswith(".mp4"):
        continue

    camera = Path(video).stem

    out_folder = os.path.join(OUTPUT_FOLDER, camera)

    os.makedirs(out_folder, exist_ok=True)

    video_path = os.path.join(VIDEO_FOLDER, video)

    # 利用 ffprobe 获取影片长度
    result = subprocess.run(
        [
            "ffprobe",
            "-v","error",
            "-show_entries","format=duration",
            "-of","default=noprint_wrappers=1:nokey=1",
            video_path
        ],
        capture_output=True,
        text=True
    )

    duration = int(float(result.stdout))

    for sec in range(0, duration, INTERVAL):

        output = os.path.join(
            out_folder,
            f"{sec:06}.wav"
        )

        subprocess.run([
            "ffmpeg",
            "-y",
            "-ss", str(sec),
            "-i", video_path,
            "-t", str(DURATION),
            "-ac", "1",
            "-ar", "16000",
            output
        ])

    print(camera, "Completed")