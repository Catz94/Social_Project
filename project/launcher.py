import sys
from streamlit.web import cli as stcli

if __name__ == "__main__":
    # 模拟命令行调用 streamlit run app.py
    sys.argv = [
        "streamlit",
        "run",
        "Video_Edit_UI.py",
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())