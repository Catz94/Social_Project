"""
Module 1 - Extract Key Frames & Generate Grid Images (Using Synced Offsets)
Author: Bryan Teh
"""

import os
import json
import cv2
from PIL import Image

OFFSETS_FILE = "analysis/offsets.json"
CONFIG_FILE = "analysis/config.json"
FRAME_FOLDER = "frames"
GRID_FOLDER = "grids"
FRAME_INTERVAL = 3  # 每 3 秒抽一张

os.makedirs(FRAME_FOLDER, exist_ok=True)
os.makedirs(GRID_FOLDER, exist_ok=True)

if os.path.exists(OFFSETS_FILE):
    try:
        with open(OFFSETS_FILE, "r", encoding="utf-8") as f:
            offsets_data = json.load(f)
    except Exception as e:
        print(f"[Error] 读取 offsets.json 失败: {e}")
        exit(1)
else:
    print("[Error] 找不到 offsets.json，请先运行 0.5 模块！")
    exit(1)

active_cameras = list(offsets_data.keys()) if offsets_data else ["camera1"]
main_cam = "camera1" if "camera1" in active_cameras else active_cameras[0]

# 计算剪辑片段的总时长
cam1_range = offsets_data.get(main_cam, {}).get("target_range", [0, 210])
MASTER_DURATION = int(cam1_range[1] - cam1_range[0]) if len(cam1_range) == 2 else 210

print("=" * 50)
print(f"Active Cameras: {active_cameras} | 片段总时长: {MASTER_DURATION} 秒")
print("=" * 50)

# ==========================================
# 1. 抽取各个机位的影格 (每 3 秒抽一张，统一叠加 offset 物理偏移)
# ==========================================
for camera_name, info in offsets_data.items():
    video_path = info.get("path", "")
    if not os.path.exists(video_path):
        print(f"[Warning] 视频文件不存在，跳过 {camera_name}: {video_path}")
        continue

    output_folder = os.path.join(FRAME_FOLDER, camera_name)
    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        target_range = info.get("target_range", [0, 9999])
        offset = info.get("offset", 0.0)
        
        # 该机位在原视频中的真实起始物理秒数 (考虑了声学 offset 偏移)
        phys_start_sec = target_range[0] + offset

        saved = 0
        for t_main in range(0, MASTER_DURATION + 1, FRAME_INTERVAL):
            phys_time = phys_start_sec + t_main  # 映射回原视频的时间戳
            
            # 若该机位在此相对时刻尚未开机，跳过该帧的提取
            if phys_time < 0:
                continue

            frame_number = int(phys_time * fps)
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            success, frame = cap.read()
            if not success:
                break

            filename = f"frame_{t_main:06d}.jpg"
            output_path = os.path.join(output_folder, filename)
            cv2.imwrite(output_path, frame)
            saved += 1

        print(f"[{camera_name}] 抽帧完成: 映射原视频物理时间 ({phys_start_sec:.1f}s -> {phys_start_sec + MASTER_DURATION:.1f}s) | 保存 {saved} 张")
    finally:
        cap.release()

# ==========================================
# 2. 自动生成多视角 Grid 拼接图
# ==========================================
if len(active_cameras) >= 2:
    print("\n📸 正在生成 AI 多视角对齐 Grid 拼接图...")
    ref_folder = os.path.join(FRAME_FOLDER, main_cam)

    if os.path.exists(ref_folder):
        frames_ref = sorted(os.listdir(ref_folder))
        for f_name in frames_ref:
            valid_imgs = []
            for cam in active_cameras:
                p = os.path.join(FRAME_FOLDER, cam, f_name)
                if os.path.exists(p):
                    valid_imgs.append(Image.open(p).resize((640, 360)))

            if valid_imgs:
                grid_width = 640 * len(valid_imgs)
                grid_img = Image.new('RGB', (grid_width, 360))
                for idx, img in enumerate(valid_imgs):
                    grid_img.paste(img, (idx * 640, 0))
                grid_img.save(os.path.join(GRID_FOLDER, f_name))

print("\n🎉 1.0 模块运行完成！影格已按照声学 Offset 精准抽帧！")
