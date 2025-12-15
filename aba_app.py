import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(
    page_title="ABA 行動変容分析アプリ (マニュアル付)",
    page_icon="📈",
    layout="wide",
)

# --- CSSスタイル（見やすさ向上） ---
st.markdown("""
<style>
    .big-font { font-size:22px !important; font-weight:bold; }
    /* 成功（緑） */
    .success-box {
        background-color: #d4edda; color: #155724; border: 2px solid #c3e6cb;
        padding: 20px; border-radius: 15px; margin-bottom: 20px;
    }
    /* 注意（黄） */
    .warning-box {
        background-color: #fff3cd; color: #856404; border: 2px solid #ffeeba;
        padding: 20px; border-radius: 15px; margin-bottom: 20px;
    }
    /* 危険/悪化（赤） */
    .danger-box {
        background-color: #f8d7da; color: #721c24; border: 2px solid #f5c6cb;
        padding: 20px; border-radius: 15px; margin-bottom: 20px;
    }
    .manual-step {
        background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 10px;
        border-left: 5px solid #007bff;
    }
</style>
""", unsafe_allow_html=True)

# --- サンプルデータ ---
template_csv = """ID,日時,対象行動,頻度,持続時間(分),強度,フェーズ,備考
1,2023-10-01 10:00,自傷行為,5,2,3,ベースライン,
2,2023-10-02 11:00,自傷行為,6,3,4,ベースライン,
3,2023-10-03 14:00,自傷行為,8,5,5,ベースライン,悪天候
4,2023-10-04 10:30,自傷行為,5,2,3,ベースライン,
5,2023-10-05 09:00,自傷行為,7,4,4,ベースライン,
6,2023-10-06 15:00,自傷行為,9,6,5,ベースライン,
7,2023-10-07 12:00,自傷行為,8,5,5,ベースライン,
8,2023-10-08 10:00,自傷行為,3,2,3,介入期,★絵カード導入
9,2023-10-09 11:00,自傷行為,2,1,2,介入期,
10,2023-10-10 14:00,自傷行為,1,1,1,介入期,
11,2023-10-11 10:00,自傷行為,1,0.5,1,介入期,
12,2023-10-12 09:00,自傷行為,0,0,0,介入期,発生なし
13,2023-10-13 15:00,自傷行為,1,0.5,1,介入期,
14,2023-10-14 12:00,自傷行為,0,0,0,介入期,
"""

# --- メインタイトル ---
st.title("📈 ABA 行動変容分析アプリ")

# --- タブの設定 ---
tab_main, tab_manual = st.tabs(["🚀 分析ツール", "📖 使い方・マニュアル"])

# ==========================================
# タブ1: 分析ツール（メイン機能）
# ==========================================
with tab_main:
    st.write("行動データを時系列で可視化し、**支援（介入）の前と後で行動がどう変わったか**を判定します。")

    # --- サイドバー ---
    with st.sidebar:
        st.header("📂 データ入力")
        st.download_button(
            label="📄 サンプルデータをDL",
            data=template_csv.encode('utf-8-sig'),
            file_name="aba_sample_data.csv",
            mime="text/csv",
        )
        uploaded_file = st.file_uploader("CSVをアップロード", type=["csv"])
        
        st.info("💡 データの作り方は「使い方マニュアル」タブをご覧ください。")

    if uploaded_file is None:
        st.info("👈 左側のメニューからCSVファイルをアップロードしてください（サンプルDL推奨）。")
    else:
        # --- データ読み込み ---
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            df.columns = df.columns.str.strip()
            
            if '日時' in df.columns:
                df['日時'] = pd.to_datetime(df['日時'], errors='coerce')
                df.dropna(subset=['日時'], inplace=True)
                df['日付'] = df['日時'].dt.date
            else:
                st.error("❌ '日時'列が見つかりません。マニュアルを確認してください。")
                st.stop()
                
            # --- 設定 ---
            st.markdown("---")
            col_set1, col_set2 = st.columns(2)
            
            with col_set1:
                if '対象行動' in df.columns:
                    selected_behavior = st.selectbox("🔍 分析する行動", df['対象行動'].unique())
                else:
                    selected_behavior = None
            
            with col_set2:
                goal_direction = st.radio(
                    "この行動はどうなると良い？", 
                    ("減らしたい（問題行動など）", "増やしたい（適切な行動など）")
                )
                
            use_daily_agg = st.checkbox("1日ごとの合計・平均で見る（推奨）", value=True)

            # --- データ加工 ---
            df_target = df[df['対象行動'] == selected_behavior].copy()
            if df_target.empty: st.stop()

            if use_daily_agg:
                agg_rules = {}
                if '頻度' in df_target.columns: agg_rules['頻度'] = 'sum'
                if '持続時間(分)' in df_target.columns: agg_rules['持続時間(分)'] = 'sum'
                if '強度' in df_target.columns: agg_rules['強度'] = 'mean'
                # 日付とフェーズで集計
                df_plot = df_target.groupby(['日付', 'フェーズ']).agg(agg_rules).reset_index().sort_values('日付')
                x_col = '日付'
            else:
                df_plot = df_target.sort_values('日時')
                x_col = '日時'

            # --- 分析ロジック ---
            st.markdown("---")
            st.subheader(f"📊 「{selected_behavior}」の変化レポート")

            y_axis_option = st.selectbox("何を確認しますか？", [c for c in ['頻度', '持続時間(分)', '強度'] if c in df_plot.columns])

            if y_axis_option and 'フェーズ' in df_plot.columns:
                unique_phases = df_plot['フェーズ'].unique()
                
                # 自動判定
                if len(unique_phases) >= 2:
                    phase_a = unique_phases[0] # ベースライン
                    phase_b = unique_phases[-1] # 介入期
                    
                    mean_a = df_plot[df_plot['フェーズ'] == phase_a][y_axis_option].mean()
                    mean_b = df_plot[df_plot['フェーズ'] == phase_b][y_axis_option].mean()
                    
                    percent_change = ((mean_b - mean_a) / mean_a) * 100 if mean_a != 0 else 0
                    
                    # 判定メッセージ生成
                    result_title = ""
                    result_msg = ""
                    css_class = ""
                    
                    # 減らしたい場合
                    if goal_direction == "減らしたい（問題行動など）":
                        if percent_change <= -50:
                            result_title = "🎉 素晴らしい効果です！"
                            result_msg = f"行動が **{abs(percent_change):.0f}% 減少** しました。支援の効果がはっきりと出ています。"
                            css_class = "success-box"
                        elif percent_change < 0:
                            result_title = "✅ 少し良くなっています"
                            result_msg = f"行動が **{abs(percent_change):.0f}% 減少** しました。このまま支援を続けましょう。"
                            css_class = "success-box"
                        else:
                            result_title = "⚠️ 変化がないか、増えています"
                            result_msg = "行動の減少が見られません。支援方法を見直す必要があるかもしれません。"
                            css_class = "danger-box"
                    
                    # 増やしたい場合
                    else:
                        if percent_change >= 50:
                            result_title = "🎉 素晴らしい効果です！"
                            result_msg = f"行動が **{abs(percent_change):.0f}% 増加** しました。支援の効果がはっきりと出ています。"
                            css_class = "success-box"
                        elif percent_change > 0:
                            result_title = "✅ 少し良くなっています"
                            result_msg = f"行動が **{abs(percent_change):.0f}% 増加** しました。このまま支援を続けましょう。"
                            css_class = "success-box"
                        else:
                            result_title = "⚠️ 変化がないか、減っています"
                            result_msg = "目的の行動が増えていません。支援方法を見直す必要があるかもしれません。"
                            css_class = "danger-box"

                    # 結果表示
                    st.markdown(f"""
                    <div class="{css_class}">
                        <div class="big-font">{result_title}</div>
                        <p>{result_msg}</p>
                        <hr style="border-top: 1px dashed #999;">
                        <b>数値の変化（平均）:</b> {phase_a}: {mean_a:.1f} ➡ {phase_b}: {mean_b:.1f}
                    </div>
                    """, unsafe_allow_html=True)

                # グラフ描画
                fig = px.line(df_plot, x=x_col, y=y_axis_option, markers=True)
                
                # フェーズ変化の装飾
                if len(unique_phases) >= 2:
                    # 変わり目を探す
                    df_sorted = df_plot.sort_values(x_col)
                    # フェーズが変わる最初の日付を取得（簡易ロジック）
                    change_date = None
                    for i in range(1, len(df_sorted)):
                        if df_sorted.iloc[i]['フェーズ'] != df_sorted.iloc[i-1]['フェーズ']:
                            change_date = df_sorted.iloc[i][x_col]
                            break
                    
                    if change_date:
                        # 縦線
                        fig.add_vline(x=change_date, line_width=2, line_dash="dash", line_color="red")
                        # ラベル
                        fig.add_annotation(
                            x=change_date, y=1.05, yref="paper",
                            text="⬇ 支援開始", showarrow=False,
                            font=dict(color="red", size=14, weight="bold")
                        )
                        # 背景色（介入期）
                        fig.add_vrect(
                            x0=change_date, x1=df_plot[x_col].max(),
                            fillcolor="green", opacity=0.1, layer="below"
                        )

                # レイアウト調整（文字サイズ等）
                fig.update_layout(
                    height=500,
                    xaxis_title="日付", yaxis_title=y_axis_option,
                    font=dict(size=14, family="Arial")
                )
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

# ==========================================
# タブ2: 使い方・マニュアル
# ==========================================
with tab_manual:
    st.header("📖 データのとり方・アプリの使い方")
    
    st.markdown("""
    ### 1. ABA（応用行動分析）の基本
    このアプリでは、**「A-Bデザイン」**という手法を使って分析します。
    
    *   **A：ベースライン期（支援前）**
        *   何も特別な支援をしていない、普段の状態の期間です。
        *   「いつもどれくらい行動が起きているか？」を知るために記録します。
    *   **B：介入期（支援中）**
        *   絵カードや褒めるなどの「支援」を始めた後の期間です。
        *   「支援によって行動がどう変わったか？」を見るために記録します。
    """)
    
    st.markdown("---")
    
    st.markdown("""
    ### 2. データ（CSV）の作り方
    Excelなどで以下の列を作成してください。特に**「フェーズ」**の列が重要です。
    """)
    
    st.markdown("""
    <div class="manual-step">
        <b>📝 必須の列名と入力ルール</b>
        <ul>
            <li><b>日時</b>: <code>2023-10-01 10:00</code> のように入力</li>
            <li><b>対象行動</b>: 行動の名前（例: 自傷行為、発語）</li>
            <li><b>数値列</b>: 以下のいずれか（または全て）を入力
                <ul>
                    <li><b>頻度</b>: 回数（例: 5）</li>
                    <li><b>持続時間(分)</b>: 長さ（例: 10）</li>
                    <li><b>強度</b>: 強さ（1〜5など）</li>
                </ul>
            </li>
            <li><b>フェーズ</b>: 🔴 <b>最重要！</b>
                <ul>
                    <li>支援前なら <code>ベースライン</code> と入力</li>
                    <li>支援後なら <code>介入期</code> （または <code>支援中</code>）と入力</li>
                </ul>
            </li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.code("日時, 対象行動, 頻度, 持続時間(分), 強度, フェーズ", language="csv")
    
    st.markdown("""
    ### 3. グラフの見方
    *   **白いエリア（左側）**: 支援をする前の状態です。
    *   **赤い点線**: 「ここから支援を始めた」という合図です。
    *   **緑のエリア（右側）**: 支援を始めた後の状態です。
    
    この2つのエリアを見比べて、**「グラフが下がった（または上がった）」** なら、あなたの支援は成功しています！🎉
    """)