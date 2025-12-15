import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(
    page_title="ABA データ可視化アプリ (介入効果分析)",
    page_icon="📈",
    layout="wide",
)

# --- サンプルデータ（介入の効果が明確にわかるもの） ---
# 10/1-10/7: ベースライン（高止まり）
# 10/8-: 介入開始（急激に減少）
template_csv = """ID,日時,対象行動,頻度,持続時間(分),強度,フェーズ,備考
1,2023-10-01 10:00,他害行為,5,2,3,ベースライン,
2,2023-10-02 11:00,他害行為,6,3,4,ベースライン,
3,2023-10-03 14:00,他害行為,8,5,5,ベースライン,調子が悪い
4,2023-10-04 10:30,他害行為,5,2,3,ベースライン,
5,2023-10-05 09:00,他害行為,7,4,4,ベースライン,
6,2023-10-06 15:00,他害行為,9,6,5,ベースライン,
7,2023-10-07 12:00,他害行為,8,5,5,ベースライン,
8,2023-10-08 10:00,他害行為,4,2,3,介入期,★介入開始（絵カード提示）
9,2023-10-09 11:00,他害行為,3,1,2,介入期,
10,2023-10-10 14:00,他害行為,2,1,1,介入期,
11,2023-10-11 10:00,他害行為,1,0.5,1,介入期,
12,2023-10-12 09:00,他害行為,0,0,0,介入期,発生なし
13,2023-10-13 15:00,他害行為,1,0.5,1,介入期,
14,2023-10-14 12:00,他害行為,0,0,0,介入期,
"""

# --- メイン画面 ---
st.title("📈 応用行動分析 (ABA) データ可視化アプリ")
st.write("行動の変化を時系列で追跡します。介入前後の変化を視覚的に強調表示します。")

# --- サイドバー ---
with st.sidebar:
    st.header("1. データ準備")
    st.download_button(
        label="📄 サンプルCSVをダウンロード",
        data=template_csv.encode('utf-8-sig'),
        file_name="aba_sample_intervention.csv",
        mime="text/csv",
        help="介入後に数値が下がるサンプルデータが含まれています。"
    )
    
    st.header("2. ファイルアップロード")
    uploaded_file = st.file_uploader(
        "CSVファイルをアップロード",
        type=["csv"],
        label_visibility="collapsed"
    )

if uploaded_file is None:
    st.info("👈 サイドバーからCSVファイルをアップロードしてください。サンプルを使って動作確認もできます。")
    st.stop()

# --- データ読み込みと前処理 ---
try:
    df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()

    if '日時' in df.columns:
        df['日時'] = pd.to_datetime(df['日時'], errors='coerce')
        df.dropna(subset=['日時'], inplace=True)
        # 分析用に日付列（時刻なし）を作成
        df['日付'] = df['日時'].dt.date
    else:
        st.error("❌ '日時'列が見つかりません。")
        st.stop()

except Exception as e:
    st.error(f"❌ ファイル読み込みエラー: {e}")
    st.stop()

# --- 分析条件設定 ---
with st.sidebar:
    st.header("3. 表示設定")
    
    if '対象行動' in df.columns:
        behavior_options = df['対象行動'].unique()
        selected_behavior = st.selectbox("分析する行動", behavior_options)
    else:
        selected_behavior = None
        
    st.markdown("---")
    # ABA的ロジック: 日次集計をするかどうか
    use_daily_agg = st.checkbox("日ごとに集計して表示", value=True, help="1日に複数回記録がある場合、合計値または平均値でグラフを描画します。")

# データのフィルタリング
df_target = df[df['対象行動'] == selected_behavior].copy()

if df_target.empty:
    st.warning("データがありません。")
    st.stop()

# --- 集計ロジック ---
if use_daily_agg:
    # 日付ごと、かつフェーズごとに集計
    # フェーズが変わる日を考慮して先頭のフェーズを採用
    agg_rules = {}
    if '頻度' in df_target.columns: agg_rules['頻度'] = 'sum'
    if '持続時間(分)' in df_target.columns: agg_rules['持続時間(分)'] = 'sum'
    if '強度' in df_target.columns: agg_rules['強度'] = 'mean'
    
    # 日付とフェーズでグループ化（同じ日にフェーズが変わることは稀と仮定）
    df_plot = df_target.groupby(['日付', 'フェーズ']).agg(agg_rules).reset_index()
    # 日付順に並べ替え
    df_plot = df_plot.sort_values('日付')
    x_col = '日付'
else:
    # 生データ（日時順）
    df_plot = df_target.sort_values('日時')
    x_col = '日時'

# --- グラフ描画（ブラッシュアップ箇所） ---
st.markdown("---")
st.subheader(f"📊 {selected_behavior} の変化推移")

y_axis_option = st.selectbox(
    "グラフの縦軸",
    [col for col in ['頻度', '持続時間(分)', '強度'] if col in df_plot.columns]
)

if y_axis_option:
    # 1. 基本の折れ線グラフ（線はつなげる）
    fig = px.line(
        df_plot, 
        x=x_col, 
        y=y_axis_option,
        markers=True,
        title=f'{selected_behavior}：{y_axis_option}の推移',
        labels={x_col: '日付', y_axis_option: y_axis_option}
    )

    # 2. フェーズ変更の強調表示ロジック
    if 'フェーズ' in df_plot.columns:
        # フェーズのリストを取得（出現順）
        phases = df_plot['フェーズ'].unique()
        
        # 最初のフェーズ以外（＝介入開始など）の開始日を特定
        # データの変わり目を探索
        df_plot_sorted = df_plot.sort_values(x_col)
        df_plot_sorted['prev_phase'] = df_plot_sorted['フェーズ'].shift(1)
        
        # フェーズが変わった行を抽出
        change_points = df_plot_sorted[
            (df_plot_sorted['prev_phase'].notna()) & 
            (df_plot_sorted['prev_phase'] != df_plot_sorted['フェーズ'])
        ]

        colors = ["rgba(0, 0, 0, 0)", "rgba(255, 0, 0, 0.05)", "rgba(0, 0, 255, 0.05)"] # 透明, 薄赤, 薄青

        for i, (index, row) in enumerate(change_points.iterrows()):
            change_date = row[x_col]
            new_phase_name = row['フェーズ']
            
            # (A) 縦線を引く（フェーズ変更線）
            fig.add_vline(
                x=change_date,
                line_width=2,
                line_dash="dash",
                line_color="red"
            )
            
            # (B) ラベルを表示
            fig.add_annotation(
                x=change_date,
                y=1.02, yref="paper",
                text=f"⬇ {new_phase_name}開始",
                showarrow=False,
                font=dict(color="red", size=12, weight="bold"),
                xanchor="left"
            )

            # (C) 介入期の背景に色をつける（強調）
            # 変更日からデータの最後（または次の変更点）までを塗りつぶす
            # 簡易的に「変更日以降ずっと」に色をつける例
            fig.add_vrect(
                x0=change_date,
                x1=df_plot[x_col].max(),
                fillcolor="green",
                opacity=0.1,
                layer="below",
                line_width=0,
                annotation_text="介入期間", 
                annotation_position="top right"
            )

    fig.update_layout(
        xaxis_title="日付", 
        yaxis_title=y_axis_option,
        hovermode="x unified" # ホバー時に情報をまとめ表示
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- 数値による変化の確認 ---
    st.markdown("#### 💡 フェーズ間の数値比較")
    if 'フェーズ' in df_plot.columns:
        # フェーズごとの平均値を計算
        phase_means = df_plot.groupby('フェーズ')[y_axis_option].mean().reset_index()
        
        cols = st.columns(len(phase_means))
        base_value = None
        
        # フェーズ順序を維持するために再ソート（元データの出現順などが必要だが、ここでは簡易的に）
        # データ内の出現順序で表示
        unique_phases = df_plot['フェーズ'].unique()
        
        for i, phase in enumerate(unique_phases):
            mean_val = df_plot[df_plot['フェーズ'] == phase][y_axis_option].mean()
            with cols[i]:
                if i == 0:
                    st.metric(label=f"{phase} (平均)", value=f"{mean_val:.2f}")
                    base_value = mean_val
                else:
                    delta = mean_val - base_value
                    st.metric(
                        label=f"{phase} (平均)", 
                        value=f"{mean_val:.2f}",
                        delta=f"{delta:.2f}",
                        delta_color="inverse" # 減少が良いこととして緑表示
                    )

# --- データ詳細 ---
with st.expander("詳細データを見る"):
    st.dataframe(df_plot)