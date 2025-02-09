import os
import streamlit as st

font_path = os.path.abspath("ipaexg.ttf")
st.write(f"フォントパス: {font_path}")
st.write(f"フォントが存在するか: {os.path.exists(font_path)}")
