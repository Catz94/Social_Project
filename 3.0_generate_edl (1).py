"""
Module 3.0 - Generate Multi-Camera EDL with Precise Physical Timestamps
Author: Bryan Teh
"""

import os
import json
import csv

ANALYSIS_FOLDER = "analysis"
OUTPUT_FOLDER = "output"
OFFSETS_FILE = os.path.join(ANALYSIS_FOLDER, "offsets.json")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

FRAME_INTERVAL = 3

if os.path.exists(OFFSETS_FILE):
    with open(OFFSETS_FILE, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
else:
    print("[Error] 找不到 offsets.json！")
    exit(1)

main_cam = "camera1" if "camera1" in CONFIG else list(CONFIG.keys())[0]
cam1_range = CONFIG[main_cam].get("target_range", [0, 210])
base_start, base_end = cam1_range[0], cam1_range[1]
MASTER_DURATION = int(base_end - base_start)

video_file = os.path.join(ANALYSIS_FOLDER, "video_analysis.json")
video_data = {}
if os.path.exists(video_file):
    try:
        with open(video_file, "r", encoding="utf-8") as f:
            video_data = json.load(f)
    except Exception as e:
        print(f"[Warning] 读取 video_analysis.json 失败: {e}")

def format_time(seconds):
    seconds = max(0, seconds)
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"

raw_clips = []

# 遍历相对时间轴 t_main
for t_main in range(0, MASTER_DURATION, FRAME_INTERVAL):
    src_times = {}
    avail_cams = {}

    for cam, cfg in CONFIG.items():
        offset = cfg.get("offset", 0.0)
        # 精准换算该机位在当前时间点的原视频物理秒数
        phys_start = base_start + t_main + offset
        src_times[cam] = phys_start

        v_node = video_data.get(cam, {}).get(str(int(t_main)), {})

        # 校验：只有当物理秒数 >= 0（代表该相机此时已开机且有记录）时，才算作有效可用机位
        if phys_start >= 0 and v_node.get("performance", True):
            avail_cams[cam] = v_node

    # 如果没有可用的辅机位，保证默认回退到主机位
    if not avail_cams:
        avail_cams[main_cam] = {}

    # 镜头选择逻辑
    selected_cam = main_cam
    reason = "Default view"
    blur = False

    if "camera2" in avail_cams:
        selected_cam = "camera2"
        reason = "Best wide shot"
        blur = avail_cams["camera2"].get("need_face_blur", False)

        for aux_cam in avail_cams:
            if aux_cam != "camera2":
                aux_data = avail_cams[aux_cam]
                shot_type = aux_data.get("shot_type", "wide")
                score = aux_data.get("camera_score", 0)

                if shot_type in ["close", "medium"] and score >= 8:
                    selected_cam = aux_cam
                    reason = f"{aux_cam} {shot_type} cut"
                    blur = aux_data.get("need_face_blur", False)
                    break
    elif main_cam in avail_cams:
        selected_cam = main_cam
        reason = "Main view fallback"
        blur = avail_cams[main_cam].get("need_face_blur", False)

    # 主音轨严格锁定 Camera 1
    a_phys_start = base_start + t_main
    a_phys_end = a_phys_start + FRAME_INTERVAL

    raw_clips.append({
        "t_start": t_main,
        "t_end": t_main + FRAME_INTERVAL,
        "cam": selected_cam,
        "src_start": src_times[selected_cam],
        "src_end": src_times[selected_cam] + FRAME_INTERVAL,
        "audio": main_cam,
        "audio_start": a_phys_start,
        "audio_end": a_phys_end,
        "blur": blur,
        "reason": reason
    })

# 合并连续镜头
edl_rows = []
current_clip = None
sequence = 1

for clip in raw_clips:
    if current_clip is None:
        current_clip = clip
        continue

    if current_clip["cam"] == clip["cam"]:
        current_clip["t_end"] = clip["t_end"]
        current_clip["src_end"] = clip["src_end"]
        current_clip["audio_end"] = clip["audio_end"]
        current_clip["blur"] = current_clip["blur"] or clip["blur"]
    else:
        transition = "Fade In" if sequence == 1 else "Cut"
        edl_rows.append([
            sequence,
            format_time(current_clip["t_start"]),
            format_time(current_clip["t_end"]),
            current_clip["cam"],
            format_time(current_clip["src_start"]),
            format_time(current_clip["src_end"]),
            current_clip["audio"],
            format_time(current_clip["audio_start"]),
            format_time(current_clip["audio_end"]),
            transition,
            current_clip["blur"],
            "FALSE",
            current_clip["reason"]
        ])
        sequence += 1
        current_clip = clip

if current_clip:
    edl_rows.append([
        sequence,
        format_time(current_clip["t_start"]),
        format_time(current_clip["t_end"]),
        current_clip["cam"],
        format_time(current_clip["src_start"]),
        format_time(current_clip["src_end"]),
        current_clip["audio"],
        format_time(current_clip["audio_start"]),
        format_time(current_clip["audio_end"]),
        "Fade Out",
        current_clip["blur"],
        "FALSE",
        current_clip["reason"]
    ])

csv_filename = os.path.join(OUTPUT_FOLDER, "EDL.csv")
with open(csv_filename, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "sequence", "timeline_start", "timeline_end", 
        "source_camera", "source_start", "source_end", 
        "audio_source", "audio_start", "audio_end", 
        "transition", "need_face_blur", "human_review", "reason"
    ])
    writer.writerows(edl_rows)

print("=" * 60)
print(f"✅ EDL 决策表成功生成！物理起始时间与音轨已精准对应！")
print("=" * 60)