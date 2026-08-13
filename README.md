# Social_Project
# 🎬 AI Multi-Camera Automated Editing Console

An intelligent, end-to-end automated multi-camera video editing pipeline and desktop application powered by Python, Streamlit, MoviePy, and Gemini AI. 

Designed to streamline complex multi-angle video production (such as performances, events, and lectures) by automating audio synchronization, frame extraction, AI-driven visual/audio analysis, and final video rendering.

---

## 🚀 Quick Download & Installation

If you just want to run the application, download the pre-compiled installer:

* **[📥 Download mysetup.exe (v1.0.0)](https://github.com/Catz94/Social_Project/releases/download/v1.0.0/mysetup.exe)**

*Simply run the installer, and it will set up the application safely on your local user environment without requiring administrator privileges.*

---

## ✨ Key Features

* **Multi-Camera Auto-Sync**: Automatically calculates time offsets across multiple camera feeds using advanced acoustic analysis.
* **Interactive Web-Based UI**: Built with Streamlit and wrapped for a smooth native desktop application experience.
* **AI-Powered Decision Making**: Integrates Google Gemini API to analyze visual frames and audio tracks, intelligently generating an Edit Decision List (EDL).
* **Modular Pipeline Architecture**: Divided into independent script-based steps, allowing both fully automated execution and developer-controlled selective runs.
* **Automated Rendering**: Exports a polished final multi-camera edited video seamlessly using MoviePy.

---

## 🔄 System Pipeline Workflow

The project processes multi-camera footage through a robust 7-step pipeline:

1. **`0.5_auto_sync_offsets.py`** - Multi-Camera Acoustic Auto-Sync
2. **`1.0_extract_frames.py`** - Frame Extraction from video feeds
3. **`1.5_extract_audio.py`** - Audio track extraction for analysis
4. **`2.0_analyze_frames.py`** - AI Visual Analysis (Gemini)
5. **`2.5_analyze_audio.py`** - AI Audio Analysis & Content Evaluation
6. **`3.0_generate_edl.py`** - EDL (Edit Decision Table) Generation
7. **`4.0_render_video.py`** - Final Video Rendering & Export

---

## 🖥️ How to Use

1. **Launch the Application**: Open the installed app via the desktop shortcut or executable (`launcher.exe`).
2. **Configure Video Paths**: Select your primary camera (Camera 1 - Required) and optional secondary angles (Camera 2, 3, 4) using the native file browser.
3. **Select Performance Range**: Use the interactive timeline slider to crop the exact performance segment you want to edit.
4. **Enter API Key**: Input your valid **Gemini API Key** to authorize the AI analytical models.
5. **Run Execution**: Click **"Start Execution"** to trigger the automated pipeline. Once finished, your final video will automatically open in the `output/` directory.

---

## 🛠️ Developer Setup (Running from Source)

If you wish to run or modify the source code locally:

1. **Clone the repository**:
   ```bash
   git clone [https://github.com/Catz94/Social_Project.git](https://github.com/Catz94/Social_Project.git)
   cd Social_Project

