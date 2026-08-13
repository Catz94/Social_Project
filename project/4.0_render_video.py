"""
Module 4.0 - Render Video with Absolute Physical Timestamps & Continuous Master Audio
Author: Bryan Teh
"""

import os
import json
import cv2
import pandas as pd
from moviepy import VideoFileClip, concatenate_videoclips

EDL_FILE = "output/EDL.csv"
OUTPUT_VIDEO_PATH = "output/final_graduation_video.mp4"
OFFSETS_FILE = "analysis/offsets.json"

VIDEO_SOURCES = {}
if os.path.exists(OFFSETS_FILE):
    try:
        with open(OFFSETS_FILE, "r", encoding="utf-8") as f:
            offsets_data = json.load(f)
        for cam, info in offsets_data.items():
            if "path" in info and os.path.exists(info["path"]):
                VIDEO_SOURCES[cam] = info["path"]
    except Exception as e:
        print(f"[Warning] 读取 offsets.json 失败: {e}")

def time_to_seconds(time_val):
    if pd.isna(time_val):
        return 0.0
    if isinstance(time_val, (int, float)):
        return max(0.0, float(time_val))

    time_str = str(time_val).strip()
    parts = time_str.split(":")

    try:
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        return max(0.0, float(time_str))
    except ValueError:
        return 0.0

# OpenCV 人脸检测
face_cascade = None
if hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data"):
    CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if os.path.exists(CASCADE_PATH):
        face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

def blur_faces_in_frame(frame):
    if face_cascade is None:
        return frame
    bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    for x, y, w, h in faces:
        face_roi = bgr_frame[y : y + h, x : x + w]
        bgr_frame[y : y + h, x : x + w] = cv2.GaussianBlur(face_roi, (99, 99), 30)
    return cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)

def main():
    if not os.path.exists(EDL_FILE):
        print(f"[Error] 找不到剪辑决策文件: {EDL_FILE}")
        return

    print("=== 读取 EDL 剪辑决策表 ===")
    edl_df = pd.read_csv(EDL_FILE)
    print(edl_df)

    source_clips = {}
    print("\n=== 加载原始视频流 ===")
    for cam, path in VIDEO_SOURCES.items():
        if os.path.exists(path):
            print(f"加载 {cam}: {path}")
            source_clips[cam] = VideoFileClip(path)

    processed_subclips = []

    print("\n=== 开始按物理真实时间轴进行纯视觉切片 ===")
    for idx, row in edl_df.iterrows():
        v_cam = str(row.get("source_camera", "")).strip()
        v_start = time_to_seconds(row.get("source_start", 0))
        v_end = time_to_seconds(row.get("source_end", 0))

        blur_flag = str(row.get("need_face_blur", False)).lower() in ["true", "1", "yes"]

        if v_cam not in source_clips or v_end <= v_start:
            continue

        print(f"Segment {idx+1:02d}: 画面[{v_cam}] 切片范围 ({v_start:.1f}s -> {v_end:.1f}s)")

        # 截取原视频物理时间段
        subclip = source_clips[v_cam].subclipped(v_start, v_end)

        if blur_flag and face_cascade is not None:
            subclip = subclip.image_transform(blur_faces_in_frame)

        processed_subclips.append(subclip)

    if not processed_subclips:
        print("[Error] 没有生成任何有效的视频片段！")
        return

    print("\n=== 正在拼接纯画面流 ===")
    final_video = concatenate_videoclips(processed_subclips, method="compose")

    # 从 Camera 1 截取整段连续的选区音频作为唯一主音轨
    main_cam = "camera1" if "camera1" in source_clips else list(source_clips.keys())[0]
    
    first_row = edl_df.iloc[0]
    last_row = edl_df.iloc[-1]
    a_start = time_to_seconds(first_row.get("audio_start", 0))
    a_end = time_to_seconds(last_row.get("audio_end", final_video.duration))

    print(f"\n=== 绑定连续无缝主音轨 [{main_cam}] ({a_start:.1f}s -> {a_end:.1f}s) ===")
    master_audio_clip = source_clips[main_cam].subclipped(a_start, a_end).audio
    final_clip = final_video.with_audio(master_audio_clip)

    print(f"\n=== 开始导出成片至: {OUTPUT_VIDEO_PATH} ===")
    final_clip.write_videofile(
        OUTPUT_VIDEO_PATH,
        codec="libx264",
        audio_codec="aac",
        fps=30,
        preset="medium"
    )

    for clip in source_clips.values():
        clip.close()
    final_clip.close()

    print("\n🎉 成片渲染完成！")
    # 假设你的输出目录路径变量叫 output_folder
    output_folder = "output"  # 请替换为你代码中实际的输出目录路径

    # 检查路径是否存在，然后打开
    if os.path.exists(output_folder):
        os.startfile(output_folder)
if __name__ == "__main__":
    main()