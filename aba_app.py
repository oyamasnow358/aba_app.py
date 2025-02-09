import os  # 必要なモジュールをインポート
import matplotlib as mpl
import matplotlib.font_manager as fm
import streamlit as st

font_path = "ipaexg.ttf"  # フォントのパス
if os.path.exists(font_path):  # フォントファイルが存在するか確認
    font_prop = fm.FontProperties(fname=font_path)
    mpl.rcParams["font.family"] = font_prop.get_name()
    st.write(f"フォント名: {font_prop.get_name()}")  # フォント名を確認
else:
    st.write("フォントファイルが見つかりません")
