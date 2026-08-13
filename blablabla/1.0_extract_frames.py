"""
Module 1 - Extract Key Frames

Author : Bryan Lim
Project : AI-Assisted Multi-Camera Kindergarten Graduation Video Editing Pipeline

Description:
-------------
This module automatically scans all MP4 files inside the "videos" folder,
extracts one frame every N seconds, saves them into the "frames" folder,
and generates a metadata.csv file for later AI analysis.

Folder Structure:

project/
│
├── videos/
│      camera1.mp4
│      camera2.mp4
│      camera4.mp4
│
├── frames/
│      camera1/
│      camera2/
│      camera4/
│
├── metadata.csv
│
└── extract_frames.py
"""
"""
Module 1 - Extract Key Frames & Generate Grid Images
Author: Bryan Teh
Project: AI-Assisted Multi-Camera Video Editing Pipeline
"""

import os
import csv
import cv2
from pathlib import Path
from PIL import Image

VIDEO_FOLDER = "videos"
FRAME_FOLDER = "frames"
GRID_FOLDER = "grids"
FRAME_INTERVAL = 3  # 每 3 秒抽一张
SUPPORTED_FORMAT = [".mp4", ".mov", ".avi", ".mkv"]

os.makedirs(FRAME_FOLDER, exist_ok=True)
os.makedirs(GRID_FOLDER, exist_ok=True)

metadata = []
video_files = [f for f in os.listdir(VIDEO_FOLDER) if Path(f).suffix.lower() in SUPPORTED_FORMAT]

print("="*50)
print(f"Found Videos: {video_files}")
print("="*50)

# 1. 抽取各个角色的影格
for video_name in video_files:
    camera_name = Path(video_name).stem
    output_folder = os.path.join(FRAME_FOLDER, camera_name)
    os.makedirs(output_folder, exist_ok=True)
    
    video_path = os.path.join(VIDEO_FOLDER, video_name)
    cap = cv2.VideoCapture(video_path)
    
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        current_second = 0
        saved = 0
        
        while current_second <= duration:
            frame_number = int(current_second * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            success, frame = cap.read()
            if not success:
                break
                
            filename = f"frame_{current_second:06d}.jpg"
            output_path = os.path.join(output_folder, filename)
            cv2.imwrite(output_path, frame)
            
            metadata.append([camera_name, current_second, filename])
            saved += 1
            current_second += FRAME_INTERVAL
            
        print(f"[{camera_name}] Duration: {duration:.2f}s | Saved: {saved} frames")
    finally:
        cap.release()

# 2. 自动生成多视角拼接图 (3合1 Grid)，极大减少 API 传输开销
cameras = [Path(f).stem for f in video_files]
if len(cameras) >= 3:
    print("\nGenerating Camera Grid Sheets for Gemini...")
    cam1, cam2, cam4 = sorted(cameras)[:3]
    
    frames_c1 = sorted(os.listdir(os.path.join(FRAME_FOLDER, cam1)))
    for f_name in frames_c1:
        p1 = os.path.join(FRAME_FOLDER, cam1, f_name)
        p2 = os.path.join(FRAME_FOLDER, cam2, f_name)
        p4 = os.path.join(FRAME_FOLDER, cam4, f_name)
        
        if os.path.exists(p1) and os.path.exists(p2) and os.path.exists(p4):
            img1 = Image.open(p1).resize((640, 360))
            img2 = Image.open(p2).resize((640, 360))
            img4 = Image.open(p4).resize((640, 360))
            
            # 横向拼接三张图 [Camera1 | Camera2 | Camera4]
            grid_img = Image.new('RGB', (1920, 360))
            grid_img.paste(img1, (0, 0))
            grid_img.paste(img2, (640, 0))
            grid_img.paste(img4, (1280, 0))
            
            grid_img.save(os.path.join(GRID_FOLDER, f_name))

print("Completed Module 1!")