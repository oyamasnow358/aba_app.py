import matplotlib as mpl
import matplotlib.font_manager as fm

font_path = "ipaexg.ttf"
if os.path.exists(font_path):
    font_prop = fm.FontProperties(fname=font_path)
    mpl.rcParams["font.family"] = font_prop.get_name()

# 現在のフォント設定を確認
import streamlit as st
st.write(f"現在のmatplotlibフォント設定: {mpl.rcParams['font.family']}")
