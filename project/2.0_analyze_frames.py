"""
Module 2 - Independent Frame Analysis (Dynamic UI & API Key Supported)
Author: Bryan Teh
"""

import os
import json
import re
import time
from PIL import Image
from google import genai
from google.genai import types

# 优先从环境变量或 UI 生成的 config.json 中动态获取 API Key
CONFIG_FILE = "analysis/config.json"
API_KEY = os.getenv("GEMINI_API_KEY", "")

if not API_KEY and os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            API_KEY = cfg.get("api_key", "")
    except Exception as e:
        print(f"[Warning] 读取 config.json 失败: {e}")

if not API_KEY or API_KEY == "-":
    raise ValueError("[Error] 未找到有效的 Gemini API Key！请先在 App 界面中输入 API Key。")

client = genai.Client(api_key=API_KEY)

FRAMES_FOLDER = "frames"
OFFSETS_FILE = "analysis/offsets.json"
OUTPUT_FILE = "analysis/video_analysis.json"
os.makedirs("analysis", exist_ok=True)

if os.path.exists(OFFSETS_FILE):
    with open(OFFSETS_FILE, "r", encoding="utf-8") as f:
        offsets_data = json.load(f)
    CAMERAS = list(offsets_data.keys())
else:
    CAMERAS = ["camera1", "camera2", "camera4"]

BATCH_SIZE = 10

DIRECTOR_PROMPT_TEMPLATE = """
You are an experienced professional video editor evaluating a frame sequence from [{camera_name}] of a kindergarten graduation ceremony video.

Camera Role Reference:
- Main/Wide shot or Close/Medium angle.

Rules:
1. Determine if stage performance is happening in this frame.
2. Rate camera composition and clarity (score 0-10).
3. Identify shot type (close, medium, wide).
4. Set need_face_blur = true ONLY if CHILDREN'S faces are clearly visible. Do NOT blur adult or teacher faces.

Evaluate ALL provided images in sequence and return ONLY a valid JSON list containing one object for EACH image:
[
  {{
    "timestamp": 0,
    "performance": true,
    "camera_score": 8,
    "shot_type": "wide",
    "need_face_blur": true,
    "reason": "Stable shot covering stage performance clearly."
  }}
]
"""

def clean_and_parse_json(text):
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)

all_results = {cam: {} for cam in CAMERAS}

for cam in CAMERAS:
    cam_folder = os.path.join(FRAMES_FOLDER, cam)
    if not os.path.exists(cam_folder):
        print(f"[Warning] 找不到目录 '{cam_folder}'，跳过 {cam}...")
        continue

    frame_files = sorted([f for f in os.listdir(cam_folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    print(f"\n" + "=" * 50)
    print(f"开始分析 {cam}: 找到 {len(frame_files)} 张图片")
    print("=" * 50)

    if not frame_files:
        print(f"[Warning] '{cam_folder}' 文件夹内没有图片文件！")
        continue

    prompt_for_cam = DIRECTOR_PROMPT_TEMPLATE.format(camera_name=cam)

    for i in range(0, len(frame_files), BATCH_SIZE):
        batch_files = frame_files[i : i + BATCH_SIZE]
        contents = [prompt_for_cam]
        batch_timestamps = []

        for f_name in batch_files:
            ts = int(re.sub(r'\D', '', f_name))
            batch_timestamps.append(ts)
            img_path = os.path.join(cam_folder, f_name)
            contents.append(f"Image for timestamp {ts} seconds:")
            contents.append(Image.open(img_path))

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )

                batch_data = clean_and_parse_json(response.text)
                if isinstance(batch_data, list):
                    for item in batch_data:
                        ts_key = str(item.get("timestamp"))
                        all_results[cam][ts_key] = item
                elif isinstance(batch_data, dict):
                    ts_key = str(batch_data.get("timestamp", batch_timestamps[0]))
                    all_results[cam][ts_key] = batch_data

                print(f"[{cam} | Batch {batch_timestamps[0]:06d}s - {batch_timestamps[-1]:06d}s] 成功解析!")
                break

            except Exception as e:
                err_msg = str(e)
                if any(err_code in err_msg for err_code in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
                    print(f"[API 拥堵/限流] 收到 {err_msg[:30]}... 等待 10 秒后重试 ({attempt+1}/{max_retries})...")
                    time.sleep(10)
                else:
                    print(f"[Error] {cam} Batch {batch_timestamps} 解析失败: {e}")

                if attempt == max_retries - 1:
                    print(f"[Fallback] 尝试耗尽，为 Batch {batch_timestamps} 填入保底数据防止空白。")
                    for ts in batch_timestamps:
                        all_results[cam][str(ts)] = {
                            "timestamp": ts,
                            "performance": True,
                            "camera_score": 6, 
                            "shot_type": "medium",
                            "need_face_blur": True,
                            "reason": "Fallback default due to API error."
                        }

        time.sleep(2)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_results, f, indent=4, ensure_ascii=False)

print(f"\n画面分析完成！结果已写入 -> {OUTPUT_FILE}")