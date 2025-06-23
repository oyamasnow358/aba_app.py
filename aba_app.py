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

# --- CSVテンプレート ---
# 注: skiprows=14 は15行目から読み込むことを意味するため、説明文と合わせる
template_csv = """このCSVファイルは、応用行動分析のデータひな形です。
"説明は14行目まで続きます。15行目以降に実際のデータを入力してください。"
'【各列の説明】
'- ID: レコード番号（任意）
'- 日時: 行動が記録された日付・時刻（例: 2023-06-15 14:30）
'- 対象行動: 行動の種類（例: 問題行動, 適応行動, 要求行動など）
'- 頻度: その行動が発生した回数（数値）
'- 持続時間(分): 行動の持続時間（分単位の数値）
'- 強度: 行動の強度（例: 1〜5の評価）
'- フェーズ: 介入などのフェーズ区分（例: ベースライン, 介入期, 維持期など）
'- 備考: その他の記録（任意）
'
'（この行まで説明です）
'
'
ID,日時,対象行動,頻度,持続時間(分),強度,フェーズ,備考
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
    st.write("以下のテンプレートを参考にCSVファイルを作成してください。")
    st.download_button(
        label="📄 CSVテンプレートをダウンロード",
        data=template_csv.encode('utf-8-sig'),
        file_name="aba_template.csv",
        mime="text/csv",
        help="説明は14行目まで記載されています。データは15行目から入力してください。"
    )
    
    st.header("2. ファイルアップロード")
    uploaded_file = st.file_uploader(
        "CSVファイルをアップロード",
        type=["csv"],
        label_visibility="collapsed"
    )

# --- ファイルがアップロードされていない場合の表示 ---
if uploaded_file is None:
    st.info("👈 サイドバーからCSVファイルをアップロードすると、分析が開始されます。")
    st.stop()

# --- データ読み込みと前処理 ---
try:
    # テンプレートに合わせて14行をスキップ
    df = pd.read_csv(uploaded_file, skiprows=14, encoding='utf-8-sig')
    
    # 日時列の変換
    if '日時' in df.columns:
        df['日時'] = pd.to_datetime(df['日時'], errors='coerce')
        if df['日時'].isnull().any():
            st.warning("⚠️ '日時'列に変換できない値が含まれています。その行は無視されます。")
            df.dropna(subset=['日時'], inplace=True)
    else:
        st.error("❌ '日時'列が見つかりません。テンプレートに従ってファイルを作成してください。")
        st.stop()

except Exception as e:
    st.error(f"❌ ファイル読み込みエラー: {e}")
    st.stop()

# --- サイドバーでの分析条件設定 ---
with st.sidebar:
    st.header("3. 分析条件の設定")
    
    # 対象行動の選択
    behavior_options = df['対象行動'].unique()
    selected_behaviors = st.multiselect(
        "分析する対象行動を選択",
        options=behavior_options,
        default=behavior_options
    )
    
    # 分析期間の選択
    min_date = df['日時'].min().date()
    max_date = df['日時'].max().date()
    start_date, end_date = st.date_input(
        "分析期間を選択",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Streamlitのdate_inputはdatetime.dateを返すため、datetime.datetimeに変換
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

# --- 分析結果の表示 ---
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
        df_filtered,
        x='日時',
        y=y_axis_option,
        color='対象行動',
        markers=True,
        title=f'{y_axis_option}の時系列推移',
        labels={'日時': '日付', y_axis_option: y_axis_option, '対象行動': '行動の種類'}
    )
    fig_time.update_layout(legend_title_text='行動の種類')

    # フェーズの境界線を追加
    if 'フェーズ' in df_filtered.columns:
        df_sorted = df_filtered.sort_values("日時").dropna(subset=['フェーズ'])
        phase_changes = df_sorted[df_sorted['フェーズ'] != df_sorted['フェーズ'].shift(1)]
        for index, row in phase_changes.iterrows():
            if index > 0: # 最初のデータポイントには線を引かない
                fig_time.add_vline(
                    x=row['日時'],
                    line_width=2,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text=f"「{row['フェーズ']}」開始",
                    annotation_position="top left"
                )
    st.plotly_chart(fig_time, use_container_width=True)
else:
    st.warning("分析可能な数値列（頻度、持続時間(分)、強度）が見つかりません。")

# 2. サマリー統計
st.subheader("サマリー統計")
col1, col2, col3 = st.columns(3)

# 各対象行動の割合 (円グラフ)
with col1:
    st.write("**行動の発生件数割合**")
    behavior_counts = df_filtered['対象行動'].value_counts().reset_index()
    behavior_counts.columns = ['対象行動', '件数']
    fig_pie = px.pie(
        behavior_counts,
        names='対象行動',
        values='件数',
        hole=0.4,
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig_pie, use_container_width=True)

# 統計メトリクス
with col2:
    st.write("**頻度・持続時間の合計**")
    if '頻度' in df_filtered.columns:
        total_freq = df_filtered['頻度'].sum()
        col2.metric(label="総頻度（回）", value=f"{total_freq:,.0f}")
    if '持続時間(分)' in df_filtered.columns:
        total_duration = df_filtered['持続時間(分)'].sum()
        col2.metric(label="総持続時間（分）", value=f"{total_duration:,.1f}")
with col3:
    st.write("**強度・持続時間の平均**")
    if '強度' in df_filtered.columns:
        avg_intensity = df_filtered['強度'].mean()
        col3.metric(label="平均強度", value=f"{avg_intensity:.2f}")
    if '持続時間(分)' in df_filtered.columns:
        avg_duration = df_filtered['持続時間(分)'].mean()
        col3.metric(label="平均持続時間（分/回）", value=f"{avg_duration:.1f}")

# 3. 分析レポート
st.markdown("---")
st.header("📝 分析結果レポート")

# レポートテキストの自動生成
report_text = f"【応用行動分析レポート】\n"
report_text += f"分析期間: {start_date.strftime('%Y/%m/%d')} ～ {end_date.strftime('%Y/%m/%d')}\n"
report_text += f"分析対象の行動: {', '.join(selected_behaviors)}\n"
report_text += "--------------------------------------\n\n"

# フェーズごとの集計
if 'フェーズ' in df_filtered.columns:
    report_text += "■ フェーズ別サマリー\n"
    phase_summary = df_filtered.groupby('フェーズ').agg(
        件数=('日時', 'count'),
        総頻度=('頻度', 'sum') if '頻度' in df else ('日時', lambda x: 'N/A'),
        総持続時間_分=('持続時間(分)', 'sum') if '持続時間(分)' in df else ('日時', lambda x: 'N/A'),
        平均強度=('強度', 'mean') if '強度' in df else ('日時', lambda x: 'N/A')
    ).reset_index()

    for _, row in phase_summary.iterrows():
        report_text += f"【{row['フェーズ']}】\n"
        report_text += f"  - データ件数: {row['件数']}件\n"
        if '頻度' in df: report_text += f"  - 総頻度: {row['総頻度']:,} 回\n"
        if '持続時間(分)' in df: report_text += f"  - 総持続時間: {row['総持続時間_分']:.1f} 分\n"
        if '強度' in df: report_text += f"  - 平均強度: {row['平均強度']:.2f}\n"
        report_text += "\n"

report_text += "■ 自由記述欄\n\n\n"

st.text_area("レポート内容（編集・追記が可能です）", report_text, height=300)

st.download_button(
    label="📩 レポートをテキストファイルでダウンロード",
    data=report_text.encode('utf-8-sig'),
    file_name=f"aba_analysis_report_{datetime.now().strftime('%Y%m%d')}.txt",
    mime="text/plain"
)