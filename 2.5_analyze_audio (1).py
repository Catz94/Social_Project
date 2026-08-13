"""
Module 2.5 - Independent Audio Analysis (Dynamic UI & API Key Supported)
Author: Bryan Teh
"""

import os
import json
import re
import time
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

AUDIO_FOLDER = "audio"
OFFSETS_FILE = "analysis/offsets.json"
OUTPUT_FILE = "analysis/audio_analysis.json"
os.makedirs("analysis", exist_ok=True)

if os.path.exists(OFFSETS_FILE):
    with open(OFFSETS_FILE, "r", encoding="utf-8") as f:
        offsets_data = json.load(f)
    CAMERAS = list(offsets_data.keys())
else:
    CAMERAS = ["camera1", "camera2", "camera4"]

BATCH_SIZE = 1

DIRECTOR_AUDIO_PROMPT_TEMPLATE = """
You are an expert audio engineer evaluating audio clips strictly for [{camera_name}] from a kindergarten graduation ceremony.

Evaluation Criteria:
1. Performance Music Clarity: Is performance music clearly audible?
2. Noise Level: Check for crowd chatter, shouting, or camera movement noise.
3. Audio Distortions: Identify clipping, muffled sound, or wind noise.

Return ONLY a valid JSON list containing one object for EACH timestamp:
[
    {{
        "timestamp": 0,
        "audio_score": 85,
        "is_clear": true,
        "reason": "Clear stage audio with minimal background noise."
    }}
]
"""

def clean_and_parse_json(text):
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)

all_audio_results = {cam: {} for cam in CAMERAS}

for cam in CAMERAS:
    cam_folder = os.path.join(AUDIO_FOLDER, cam)
    if not os.path.exists(cam_folder):
        print(f"[Warning] 找不到目录 '{cam_folder}'，跳过 {cam}...")
        continue

    audio_files = sorted([f for f in os.listdir(cam_folder) if f.lower().endswith((".wav", ".mp3"))])
    print(f"\n" + "=" * 50)
    print(f"开始分析音频 {cam}: 找到 {len(audio_files)} 个音频段")
    print("=" * 50)

    if not audio_files:
        print(f"[Warning] '{cam_folder}' 文件夹内没有音频文件！")
        continue

    prompt_for_cam = DIRECTOR_AUDIO_PROMPT_TEMPLATE.format(camera_name=cam)

    for i in range(0, len(audio_files), BATCH_SIZE):
        batch_files = audio_files[i : i + BATCH_SIZE]
        contents = [prompt_for_cam]
        uploaded_files = []
        batch_timestamps = []

        for f_name in batch_files:
            ts = int(re.sub(r'\D', '', f_name))
            batch_timestamps.append(ts)
            audio_path = os.path.join(cam_folder, f_name)

            uploaded_file = client.files.upload(file=audio_path)
            uploaded_files.append(uploaded_file)
            contents.append(f"Audio clip for timestamp {ts} seconds:")
            contents.append(uploaded_file)

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
                        all_audio_results[cam][ts_key] = item
                elif isinstance(batch_data, dict):
                    ts_key = str(batch_data.get("timestamp", batch_timestamps[0]))
                    all_audio_results[cam][ts_key] = batch_data

                print(f"[{cam} | Audio Batch {batch_timestamps[0]:06d}s - {batch_timestamps[-1]:06d}s] 成功解析!")
                break

            except Exception as e:
                err_msg = str(e)
                if any(err_code in err_msg for err_code in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
                    print(f"[API 拥堵/限流] 等待 10 秒后重试 ({attempt+1}/{max_retries})...")
                    time.sleep(10)
                else:
                    print(f"[Error] {cam} Audio Batch {batch_timestamps} 解析失败: {e}")

                if attempt == max_retries - 1:
                    print(f"[Fallback] 尝试耗尽，为 Audio Batch {batch_timestamps} 填入保底数据。")
                    for ts in batch_timestamps:
                        all_audio_results[cam][str(ts)] = {
                            "timestamp": ts,
                            "audio_score": 75,
                            "is_clear": True,
                            "reason": "Fallback default due to API limit."
                        }

        for uf in uploaded_files:
            try:
                client.files.delete(name=uf.name)
            except Exception:
                pass

        time.sleep(1.5)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_audio_results, f, indent=4, ensure_ascii=False)

print(f"\n音频分析完成！结果已写入 -> {OUTPUT_FILE}")