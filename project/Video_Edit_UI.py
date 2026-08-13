"""
Main UI Entrypoint - Streamlit UI for Multi-Camera Alignment Pipeline
Run via: streamlit run Video_Edit_UI.py
"""

import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import filedialog
import streamlit as st
from moviepy import VideoFileClip


# 获取 exe 运行目录或脚本运行目录
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

# 关键修复：将当前工作目录直接切换到程序根目录
# 这样所有子脚本中的相对路径（如 analysis/、output/ 等）都会安全地创建在安装目录下
os.chdir(app_dir)

# 统一创建分析文件夹
os.makedirs("analysis", exist_ok=True)

CONFIG_FILE = "analysis/config.json"
SETTING_FILE = "analysis/offsets.json"

st.set_page_config(page_title="AI Multi-Camera Automated Editing Console", layout="wide")
st.title("🎬 AI Multi-Camera Automated Editing Console")

# ==========================================
# 0. Utility Functions & Session State Initialization
# ==========================================
default_paths = {
    "cam1_path": "",
    "cam2_path": "",
    "cam3_path": "",
    "cam4_path": "",
}

for key, val in default_paths.items():
    if key not in st.session_state:
        st.session_state[key] = val

def browse_video_file(session_key):
    """Open native Windows file dialog and save path"""
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)
    selected_file = filedialog.askopenfilename(
        title="Select Video File",
        filetypes=[
            ("Video Files", "*.mp4 *.mov *.avi *.mkv *.flv *.wmv"),
            ("All Files", "*.*")
        ]
    )
    root.destroy()
    if selected_file:
        st.session_state[session_key] = selected_file

def format_mmss(seconds: int) -> str:
    """Convert seconds to mm:ss format"""
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins:02d}:{secs:02d}"

# ==========================================
# 1. Camera Configuration
# ==========================================
st.subheader("1. Configure Camera Video Paths")
col1, col2, col3, col4 = st.columns(4)

# Camera 1
with col1:
    st.markdown("**Camera 1 (Base View - Required)**")
    c_in1, c_btn1 = st.columns([3, 1])
    with c_in1:
        cam1_path = st.text_input("Cam1", key="cam1_path", label_visibility="collapsed")
    with c_btn1:
        st.button("📂 Browse", key="btn_cam1", on_click=browse_video_file, args=("cam1_path",))

# Camera 2
with col2:
    st.markdown("**Camera 2 (Optional)**")
    c_in2, c_btn2 = st.columns([3, 1])
    with c_in2:
        cam2_path = st.text_input("Cam2", key="cam2_path", label_visibility="collapsed")
    with c_btn2:
        st.button("📂 Browse", key="btn_cam2", on_click=browse_video_file, args=("cam2_path",))

# Camera 3
with col3:
    st.markdown("**Camera 3 (Optional)**")
    c_in3, c_btn3 = st.columns([3, 1])
    with c_in3:
        cam3_path = st.text_input("Cam3", key="cam3_path", label_visibility="collapsed")
    with c_btn3:
        st.button("📂 Browse", key="btn_cam3", on_click=browse_video_file, args=("cam3_path",))

# Camera 4
with col4:
    st.markdown("**Camera 4 (Optional)**")
    c_in4, c_btn4 = st.columns([3, 1])
    with c_in4:
        cam4_path = st.text_input("Cam4", key="cam4_path", label_visibility="collapsed")
    with c_btn4:
        st.button("📂 Browse", key="btn_cam4", on_click=browse_video_file, args=("cam4_path",))

st.markdown("---")

# ==========================================
# 2. Performance Range Selection
# ==========================================
st.subheader("2. Select Performance Range (Based on Camera 1)")

start_sec, end_sec = 0, 0
clean_cam1 = cam1_path.strip()

if clean_cam1 and os.path.exists(clean_cam1):
    st.video(clean_cam1)
    
    try:
        clip = VideoFileClip(clean_cam1)
        max_duration = int(clip.duration)
        clip.close()

        start_sec, end_sec = st.select_slider(
            "Drag slider to select range (mm:ss):",
            options=list(range(max_duration + 1)),
            value=(min(30, max_duration), min(210, max_duration)),
            format_func=format_mmss
        )
        
        st.info(
            f"📍 Selected Range: **{format_mmss(start_sec)}** to **{format_mmss(end_sec)}** "
            f"(Total duration: **{format_mmss(end_sec - start_sec)}**)"
        )
    except Exception as e:
        st.error(f"Failed to read Camera 1 video duration: {e}")
else:
    st.warning("⚠️ Please enter or select a valid Camera 1 video path to enable timeline selection.")

st.markdown("---")

# ==========================================
# 3. Gemini API Key Configuration
# ==========================================
st.subheader("3. Configure Gemini API Key")

saved_api_key = ""
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved_api_key = json.load(f).get("api_key", "")
    except Exception:
        pass

user_api_key = st.text_input(
    "Enter your Gemini API Key (Required):",
    value=saved_api_key,
    type="password",
    help="A valid API Key is required for Visual and Audio analysis models."
)

st.markdown("---")

# ==========================================
# 4. Developer Options
# ==========================================
st.subheader("4. Pipeline Control & Execution Settings")

dev_mode = st.checkbox("🛠️ Enable Developer Mode (Allow manual selection/exclusion of Py scripts)", value=False)

all_pipeline_steps = [
    ("0.5 Multi-Camera Acoustic Auto-Sync", "0.5_auto_sync_offsets.py"),
    ("1.0 Frame Extraction", "1.0_extract_frames.py"),
    ("1.5 Audio Extraction", "1.5_extract_audio.py"),
    ("2.0 AI Visual Analysis", "2.0_analyze_frames.py"),
    ("2.5 AI Audio Analysis", "2.5_analyze_audio.py"),
    ("3.0 Generate EDL Decision Table", "3.0_generate_edl.py"),
    ("4.0 Video Rendering & Export", "4.0_render_video.py")
]

selected_steps = []

if dev_mode:
    st.write("🔧 **Please select the scripts to execute:**")
    cols_dev = st.columns(3)
    for idx, (label, py_file) in enumerate(all_pipeline_steps):
        with cols_dev[idx % 3]:
            is_selected = st.checkbox(f"{label} (`{py_file}`)", value=True, key=py_file)
            if is_selected:
                selected_steps.append((label, py_file))
else:
    selected_steps = all_pipeline_steps

st.markdown("---")

# ==========================================
# 5. Execution Control
# ==========================================
if st.button("🚀 Start Execution", type="primary"):
    # Validation
    clean_api_key = user_api_key.strip()
    if not clean_api_key:
        st.error("❌ Execution failed: Please enter a valid Gemini API Key!")
        st.stop()

    if not clean_cam1 or not os.path.exists(clean_cam1):
        st.error("❌ Execution failed: Camera 1 is required!")
        st.stop()

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"api_key": clean_api_key}, f, indent=4, ensure_ascii=False)

    # Calculate offsets
    raw_cameras = {"camera1": cam1_path, "camera2": cam2_path, "camera3": cam3_path, "camera4": cam4_path}
    default_offsets = {"camera1": 0.0, "camera2": 0.0, "camera3": 0.0, "camera4": 0.0}
    calculated_offsets = {}
    skipped_cameras = []

    for cam_name, path in raw_cameras.items():
        clean_path = path.strip()
        if clean_path and os.path.exists(clean_path):
            offset_val = default_offsets.get(cam_name, 0.0)
            calculated_offsets[cam_name] = {
                "offset": offset_val,
                "target_range": [start_sec + offset_val, end_sec + offset_val],
                "path": clean_path
            }
        else:
            if clean_path:
                skipped_cameras.append(f"{cam_name} (Invalid path: `{clean_path}`)")
            else:
                skipped_cameras.append(f"{cam_name} (Not set)")

    if skipped_cameras:
        st.warning(f"ℹ️ Automatically skipped cameras: {', '.join(skipped_cameras)}")

    with open(SETTING_FILE, "w", encoding="utf-8") as f:
        json.dump(calculated_offsets, f, indent=4, ensure_ascii=False)
        
    st.success(f"✅ Configuration complete! {len(calculated_offsets)} active cameras.")

    # Execute Pipeline
    if not selected_steps:
        st.warning("⚠️ No scripts selected!")
    else:
        log_box = st.empty()
        status_progress = st.progress(0)
        total_steps = len(selected_steps)
        
        for step_idx, (label, py_file) in enumerate(selected_steps):
            if not os.path.exists(py_file):
                st.error(f"❌ Script not found: `{py_file}`")
                continue
                
            log_box.info(f"⏳ Running ({step_idx + 1}/{total_steps}): **{label}**...")
            
            custom_env = os.environ.copy()
            custom_env["PYTHONIOENCODING"] = "utf-8"

            result = subprocess.run(
                ["python", py_file],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=custom_env,
            )
            
            if result.returncode == 0:
                st.write(f"✅ **{label}** ran successfully!")
                if result.stdout.strip():
                    with st.expander(f"View console logs for `{py_file}`"):
                        st.code(result.stdout)
            else:
                st.error(f"❌ **{label}** interrupted with error!")
                if result.stderr.strip():
                    with st.expander(f"View traceback", expanded=True):
                        st.code(result.stderr)
                st.stop()
                
            status_progress.progress((step_idx + 1) / total_steps)

        st.balloons()
        st.success("🎉 Pipeline execution complete!")
        
        # Open output folder automatically
        output_dir = os.path.abspath("output")
        if os.path.exists(output_dir):
            try:
                os.startfile(output_dir)
            except Exception:
                pass
        
        final_video_path = "output/final_graduation_video.mp4"
        executed_files = [p for _, p in selected_steps]
        if "4.0_render_video.py" in executed_files and os.path.exists(final_video_path):
            st.subheader("🎬 Final Video Preview")
            st.video(final_video_path)