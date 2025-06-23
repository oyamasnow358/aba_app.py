import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(
    page_title="応用行動分析(ABA)データ可視化アプリ",
    page_icon="📈",
    layout="wide",
)

# --- シンプルなCSVテンプレート ---
template_csv = """ID,日時,対象行動,頻度,持続時間(分),強度,フェーズ,備考
1,2023-10-01 10:00,自傷行為,3,5,4,ベースライン,課題中
2,2023-10-01 14:30,要求行動,5,1,2,ベースライン,おやつの時間
3,2023-10-08 10:15,自傷行為,1,2,2,介入期,支援者が介入
4,2023-10-08 14:45,要求行動,8,1,1,介入期,ジェスチャー使用
"""

# --- メイン画面 ---
st.title("📈 応用行動分析 (ABA) データ可視化アプリ")
st.write("行動データを時系列で可視化し、介入の効果を分析します。")

# --- サイドバー ---
with st.sidebar:
    st.header("1. データ準備")
    st.markdown("""
    以下のボタンからテンプレートをダウンロードし、ご自身のデータに書き換えてください。
    - **1行目**は必ず**ヘッダー（列名）**にしてください。
    - **2行目**から**実際のデータ**を入力してください。
    """)
    st.download_button(
        label="📄 CSVテンプレートをダウンロード",
        data=template_csv.encode('utf-8-sig'),
        file_name="aba_template_simple.csv",
        mime="text/csv"
    )
    
    st.header("2. ファイルアップロード")
    uploaded_file = st.file_uploader(
        "CSVファイルをアップロード",
        type=["csv"],
        label_visibility="collapsed"
    )

if uploaded_file is None:
    st.info("👈 サイドバーからCSVファイルをアップロードすると、分析が開始されます。")
    st.stop()

# --- データ読み込みと前処理 ---
try:
    df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()

    if '日時' in df.columns:
        df['日時'] = pd.to_datetime(df['日時'], errors='coerce')
        if df['日時'].isnull().any():
            st.warning("⚠️ '日時'列に日付として変換できない値が含まれています。その行は分析から除外されます。")
            df.dropna(subset=['日時'], inplace=True)
    else:
        st.error(f"❌ '日時'列が見つかりません。テンプレートに従ってファイルを作成してください。")
        st.info(f"💡 **実際に読み込まれた列名:** `{list(df.columns)}`\n\nCSVファイルの1行目がヘッダー（列名）になっているか、ご確認ください。")
        st.stop()

except Exception as e:
    st.error(f"❌ ファイル読み込みエラー: {e}")
    st.stop()

# --- サイドバーでの分析条件設定 ---
with st.sidebar:
    st.header("3. 分析条件の設定")
    
    if '対象行動' in df.columns:
        behavior_options = df['対象行動'].unique()
        selected_behaviors = st.multiselect(
            "分析する対象行動を選択", options=behavior_options, default=behavior_options
        )
    else:
        st.warning("'対象行動' 列が見つかりません。")
        selected_behaviors = []
    
    min_date = df['日時'].min().date()
    max_date = df['日時'].max().date()
    start_date, end_date = st.date_input(
        "分析期間を選択", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

# データのフィルタリング
df_filtered = df[
    (df['対象行動'].isin(selected_behaviors)) &
    (df['日時'] >= start_datetime) &
    (df['日時'] <= end_datetime)
].copy()

if df_filtered.empty:
    st.warning("⚠️ 選択された条件に一致するデータがありません。")
    st.stop()

st.success(f"✅ データ読み込み完了！ **{len(df_filtered)}件**のデータを分析します。")

with st.expander("プレビュー: 分析対象データ"):
    st.dataframe(df_filtered)

st.markdown("---")
st.header("📊 分析結果")

# 1. 時系列グラフ
st.subheader("行動データの時系列グラフ")
y_axis_option = st.selectbox(
    "グラフの縦軸を選択してください",
    [col for col in ['頻度', '持続時間(分)', '強度'] if col in df_filtered.columns]
)

if y_axis_option:
    fig_time = px.line(
        df_filtered, x='日時', y=y_axis_option, color='対象行動', markers=True,
        title=f'{y_axis_option}の時系列推移',
        labels={'日時': '日付', y_axis_option: y_axis_option, '対象行動': '行動の種類'}
    )
    fig_time.update_layout(legend_title_text='行動の種類')

    # ★★★★★ ここからがエラー修正箇所 ★★★★★
    if 'フェーズ' in df_filtered.columns:
        df_sorted = df_filtered.sort_values("日時").dropna(subset=['フェーズ'])
        phase_changes = df_sorted[df_sorted['フェーズ'] != df_sorted['フェーズ'].shift(1)]
        for _, row in phase_changes.iterrows():
            # 手順1: 線だけを描画する
            fig_time.add_vline(
                x=row['日時'], line_width=2, line_dash="dash", line_color="gray"
            )
            # 手順2: テキスト注釈を別途追加する
            fig_time.add_annotation(
                x=row['日時'], y=1.05, yref="paper",
                text=f"「{row['フェーズ']}」開始",
                showarrow=False, xanchor="left",
                font=dict(color="gray", size=12)
            )
    # ★★★★★ ここまでがエラー修正箇所 ★★★★★
            
    st.plotly_chart(fig_time, use_container_width=True)
else:
    st.warning("分析可能な数値列（頻度、持続時間(分)、強度）が見つかりません。")

# --- (これ以降のコードは変更なし) ---

# 2. サマリー統計
st.subheader("サマリー統計")
col1, col2, col3 = st.columns(3)
with col1:
    st.write("**行動の発生件数割合**")
    behavior_counts = df_filtered['対象行動'].value_counts().reset_index()
    behavior_counts.columns = ['対象行動', '件数']
    fig_pie = px.pie(behavior_counts, names='対象行動', values='件数', hole=0.4)
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig_pie, use_container_width=True)
with col2:
    st.write("**頻度・持続時間の合計**")
    if '頻度' in df_filtered.columns:
        col2.metric(label="総頻度（回）", value=f"{df_filtered['頻度'].sum():,.0f}")
    if '持続時間(分)' in df_filtered.columns:
        col2.metric(label="総持続時間（分）", value=f"{df_filtered['持続時間(分)'].sum():,.1f}")
with col3:
    st.write("**強度・持続時間の平均**")
    if '強度' in df_filtered.columns:
        col3.metric(label="平均強度", value=f"{df_filtered['強度'].mean():.2f}")
    if '持続時間(分)' in df_filtered.columns:
        col3.metric(label="平均持続時間（分/回）", value=f"{df_filtered['持続時間(分)'].mean():.1f}")

# 3. 分析レポート
st.markdown("---")
st.header("📝 分析結果レポート")
report_text = f"【応用行動分析レポート】\n"
report_text += f"分析期間: {start_date.strftime('%Y/%m/%d')} ～ {end_date.strftime('%Y/%m/%d')}\n"
report_text += f"分析対象の行動: {', '.join(selected_behaviors)}\n"
report_text += "--------------------------------------\n\n"
if 'フェーズ' in df_filtered.columns:
    report_text += "■ フェーズ別サマリー\n"
    df_agg = df_filtered.copy()
    numeric_cols = df_agg.select_dtypes(include=['number']).columns
    agg_dict = {'件数': ('日時', 'count')}
    if '頻度' in numeric_cols: agg_dict['総頻度'] = ('頻度', 'sum')
    if '持続時間(分)' in numeric_cols: agg_dict['総持続時間_分'] = ('持続時間(分)', 'sum')
    if '強度' in numeric_cols: agg_dict['平均強度'] = ('強度', 'mean')
    
    if agg_dict:
        phase_summary = df_agg.groupby('フェーズ').agg(**agg_dict).reset_index()
        for _, row in phase_summary.iterrows():
            report_text += f"【{row['フェーズ']}】\n"
            report_text += f"  - データ件数: {row['件数']}件\n"
            if '総頻度' in row: report_text += f"  - 総頻度: {row['総頻度']:,} 回\n"
            if '総持続時間_分' in row: report_text += f"  - 総持続時間: {row['総持続時間_分']:.1f} 分\n"
            if '平均強度' in row: report_text += f"  - 平均強度: {row['平均強度']:.2f}\n"
            report_text += "\n"
report_text += "■ 自由記述欄\n\n\n"
st.text_area("レポート内容（編集・追記が可能です）", report_text, height=300)
st.download_button(
    "📩 レポートをテキストファイルでダウンロード", report_text.encode('utf-8-sig'),
    f"aba_analysis_report_{datetime.now().strftime('%Y%m%d')}.txt", "text/plain"
)