import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(
    page_title="ABA かんたん分析アプリ",
    page_icon="😊",
    layout="wide",
)

# --- スタイル調整（文字を大きく見やすく） ---
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight:bold; }
    .result-box { padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    .success-box { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .warning-box { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    .danger-box { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
</style>
""", unsafe_allow_html=True)

# --- サンプルデータ（劇的な改善が見られる例） ---
template_csv = """ID,日時,対象行動,頻度,持続時間(分),強度,フェーズ,備考
1,2023-10-01 10:00,他害行為,5,2,3,介入前,
2,2023-10-02 11:00,他害行為,6,3,4,介入前,
3,2023-10-03 14:00,他害行為,8,5,5,介入前,
4,2023-10-04 10:30,他害行為,5,2,3,介入前,
5,2023-10-05 09:00,他害行為,7,4,4,介入前,
6,2023-10-06 15:00,他害行為,9,6,5,介入前,
7,2023-10-07 12:00,他害行為,8,5,5,介入前,
8,2023-10-08 10:00,他害行為,2,1,2,介入後,★絵カード導入
9,2023-10-09 11:00,他害行為,1,1,1,介入後,
10,2023-10-10 14:00,他害行為,1,0.5,1,介入後,
11,2023-10-11 10:00,他害行為,0,0,0,介入後,発生なし！
12,2023-10-12 09:00,他害行為,0,0,0,介入後,
13,2023-10-13 15:00,他害行為,1,0.5,1,介入後,
14,2023-10-14 12:00,他害行為,0,0,0,介入後,
"""

# --- メイン画面 ---
st.title("😊 行動変化の分析レポート")
st.write("データをもとに、支援（介入）によって行動がどう変わったかを分かりやすく表示します。")

# --- サイドバー ---
with st.sidebar:
    st.header("1. データの準備")
    st.download_button(
        label="📄 サンプルデータをダウンロード",
        data=template_csv.encode('utf-8-sig'),
        file_name="aba_sample_result.csv",
        mime="text/csv",
    )
    uploaded_file = st.file_uploader("CSVファイルをアップロード", type=["csv"])

if uploaded_file is None:
    st.info("👈 左側のメニューからファイルをアップロードしてください。（サンプルで試すこともできます）")
    st.stop()

# --- データ読み込み ---
try:
    df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()
    if '日時' in df.columns:
        df['日時'] = pd.to_datetime(df['日時'], errors='coerce')
        df.dropna(subset=['日時'], inplace=True)
        df['日付'] = df['日時'].dt.date
    else:
        st.error("データに「日時」列が必要です。")
        st.stop()
except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    st.stop()

# --- 設定 ---
with st.sidebar:
    st.header("2. 設定")
    if '対象行動' in df.columns:
        selected_behavior = st.selectbox("分析する行動", df['対象行動'].unique())
    else:
        selected_behavior = None
    
    st.write("---")
    goal_direction = st.radio("この行動はどうなると良いですか？", ("減らしたい（問題行動など）", "増やしたい（適切な行動など）"))
    use_daily_agg = st.checkbox("1日ごとの合計で見る（推奨）", value=True)

# フィルタリングと集計
df_target = df[df['対象行動'] == selected_behavior].copy()
if df_target.empty: st.stop()

if use_daily_agg:
    agg_rules = {}
    if '頻度' in df_target.columns: agg_rules['頻度'] = 'sum'
    if '持続時間(分)' in df_target.columns: agg_rules['持続時間(分)'] = 'sum'
    if '強度' in df_target.columns: agg_rules['強度'] = 'mean'
    df_plot = df_target.groupby(['日付', 'フェーズ']).agg(agg_rules).reset_index().sort_values('日付')
    x_col = '日付'
else:
    df_plot = df_target.sort_values('日時')
    x_col = '日時'

# --- メインコンテンツ ---
st.markdown("---")
st.subheader(f"📊 「{selected_behavior}」の変化")

y_axis_option = st.selectbox("何を確認しますか？", [c for c in ['頻度', '持続時間(分)', '強度'] if c in df_plot.columns])

if y_axis_option and 'フェーズ' in df_plot.columns:
    # --- 1. 自動分析ロジック（ここが素人向け機能の核） ---
    
    # フェーズの出現順を取得
    unique_phases = df_plot['フェーズ'].unique()
    
    if len(unique_phases) >= 2:
        phase_a = unique_phases[0] # 最初のフェーズ（介入前）
        phase_b = unique_phases[-1] # 最後のフェーズ（介入後）
        
        mean_a = df_plot[df_plot['フェーズ'] == phase_a][y_axis_option].mean()
        mean_b = df_plot[df_plot['フェーズ'] == phase_b][y_axis_option].mean()
        
        diff = mean_b - mean_a
        
        # 0除算回避
        if mean_a == 0:
            ratio = 0 if mean_b == 0 else 100 # 元が0なら変化なし(0)か無限増(100扱い)
        else:
            ratio = (mean_b / mean_a) * 100 # 介入後は前の何％になったか

        percent_change = ((mean_b - mean_a) / mean_a) * 100 if mean_a != 0 else 0
        
        # 判定ロジック
        result_title = ""
        result_msg = ""
        css_class = ""
        
        # 「減らしたい行動」の場合の判定
        if goal_direction == "減らしたい（問題行動など）":
            if percent_change <= -80: # 80%以上減った
                result_title = "🎉 素晴らしい効果です！"
                result_msg = f"介入前と比較して、行動が **{abs(percent_change):.0f}% 減少** しました。劇的な改善が見られます。"
                css_class = "success-box"
            elif percent_change <= -30: # 30%以上減った
                result_title = "✅ 効果が出ています"
                result_msg = f"介入前と比較して、行動が **{abs(percent_change):.0f}% 減少** しました。この支援方法は有効そうです。"
                css_class = "success-box"
            elif percent_change < 0: # 少し減った
                result_title = "⚖️ 少し変化がありました"
                result_msg = f"わずかに減少傾向（{abs(percent_change):.0f}% 減）ですが、まだ明確な効果とは言えません。もう少し様子を見ましょう。"
                css_class = "warning-box"
            else: # 増えた、または変わらない
                result_title = "⚠️ 注意が必要です"
                result_msg = "行動の減少が見られません（むしろ増加、または変化なし）。介入方法の見直しが必要かもしれません。"
                css_class = "danger-box"

        # 「増やしたい行動」の場合の判定
        else:
            if percent_change >= 50:
                result_title = "🎉 素晴らしい効果です！"
                result_msg = f"介入前と比較して、行動が **{abs(percent_change):.0f}% 増加** しました。とても順調です。"
                css_class = "success-box"
            elif percent_change > 0:
                result_title = "✅ 良い傾向です"
                result_msg = f"少しずつ増えています（{abs(percent_change):.0f}% 増）。継続して支援しましょう。"
                css_class = "success-box"
            else:
                result_title = "⚠️ 変化が見られません"
                result_msg = "目的の行動が増えていません。支援方法を工夫する必要があるかもしれません。"
                css_class = "warning-box"

        # --- 結果の表示 ---
        st.markdown(f"""
        <div class="result-box {css_class}">
            <div class="big-font">{result_title}</div>
            <p style="margin-top:10px; font-size:16px;">{result_msg}</p>
            <hr style="border-top: 1px dashed #ccc;">
            <p><b>具体的な数字の変化:</b><br>
            「{phase_a}」の平均: <b>{mean_a:.1f}</b> <br>
            　　⬇ <br>
            「{phase_b}」の平均: <b>{mean_b:.1f}</b> </p>
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.info("データにフェーズ（期間）が1つしかありません。比較するには「介入前」「介入後」のように異なるフェーズのデータが必要です。")

    # --- 2. グラフ描画（視覚的にも分かりやすく） ---
    fig = px.line(
        df_plot, x=x_col, y=y_axis_option,
        markers=True, title=None
    )
    
    # フェーズの変わり目を視覚化
    if len(unique_phases) >= 2:
        # 変わり目の日付を取得
        df_sorted = df_plot.sort_values(x_col)
        change_points = df_sorted[df_sorted['フェーズ'] != df_sorted['フェーズ'].shift(1)].dropna()
        
        for index, row in change_points.iterrows():
            if row['フェーズ'] != unique_phases[0]: # 最初のフェーズ以外（＝介入開始）
                # 縦線
                fig.add_vline(x=row[x_col], line_width=2, line_dash="dash", line_color="red")
                # ラベル
                fig.add_annotation(
                    x=row[x_col], y=1.05, yref="paper",
                    text="ここから支援開始 ⬇", showarrow=False,
                    font=dict(color="red", size=14, weight="bold")
                )
                # 背景色（ここから右側を緑にする）
                fig.add_vrect(
                    x0=row[x_col], x1=df_plot[x_col].max(),
                    fillcolor="green", opacity=0.1, layer="below"
                )

    fig.update_layout(xaxis_title="日付", yaxis_title=y_axis_option, height=400)
    st.plotly_chart(fig, use_container_width=True)

with st.expander("詳細なデータ表を見る"):
    st.dataframe(df_plot)