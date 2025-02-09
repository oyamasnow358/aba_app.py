import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import StringIO
from datetime import datetime
import matplotlib.font_manager as fm

# 日本語フォントのパスを指定
font_path = "C:/Users/taka/OneDrive/デスクトップ/アプリ開発/応用行動分析/aba_app/ipaexg.ttf"  # フォントのパスを適宜変更
font_prop = fm.FontProperties(fname=font_path)
plt.rcParams["font.family"] = font_prop.get_name()
# ------------------------------------------
# CSVテンプレート作成用の文字列（例）
template_csv = """このCSVファイルは、応用行動分析のデータひな形です。"
"15行以降に実際のデータを入力してください。"

'【各列の説明】
'- ID: レコード番号（任意）
'- 日時: 行動が記録された日付・時刻（例: 2023-06-15 14:30）
'- 対象行動: 行動の種類（例: 問題行動、適応行動、要求行動など）
'- 頻度: その行動が発生した回数（数値）
'- 持続時間: 行動の持続時間（秒などの数値）
'- 強度: 行動の強度（例: 1〜5の評価）
'- フェーズ: 介入などのフェーズ区分（例: 介入前、介入後）
'- 備考: その他の記録（任意）
'

ID,日時,対象行動,頻度,持続時間(分),強度,フェーズ,備考
1,2023-06-15 14:30,問題行動,3,45,4,介入前,注意が必要
2,2023-06-15 15:00,適応行動,5,60,2,介入前,良好
3,2023-06-16 10:15,問題行動,2,30,5,介入後,環境の変化あり
"""

# ------------------------------------------
# タイトル・説明の表示
st.title("応用行動分析 WEB アプリ")
st.markdown("### CSVテンプレートのダウンロード")
st.write("""
以下のボタンをクリックすると、応用行動分析用のCSVファイルひな形をダウンロードできます。  
※ このテンプレートでは、**最初の3行**に各項目の説明が書かれており、**4行目以降**に実データを入力してください。
""")
st.download_button(
    label="CSVテンプレートをダウンロード",
    data=template_csv.encode('utf-8-sig'),  # utf-8-sigでエンコード
    file_name="aba_template.csv",
    mime="text/csv"
)

st.markdown("---")
st.markdown("### 応用行動分析の実行方法")
st.write("""
1. サイドバーから、上記テンプレートに沿った形式のCSVファイルをアップロードしてください。  
2. アップロード後、入力された定量データ（回数、持続時間など）に基づき、グラフが自動更新されます。  
    - **時系列グラフ**：介入前後の変化やセッションごとのばらつきが視覚的に確認できます。  
    - **フェーズ切替表示**：「フェーズ」列がある場合、フェーズの切替点に垂直線が表示され、介入効果がわかりやすくなります。  
3. グラフの下部に分析結果のサマリレポートが出力され、支援者が今後のプランに反映できる情報を提供します。
""")

# ------------------------------------------
# CSVファイルアップロードとデータ読み込み
st.sidebar.header("1. データのアップロード")
uploaded_file = st.sidebar.file_uploader("CSVファイルをアップロード", type=["csv"])

if uploaded_file is not None:
    try:
        # ヘッダーが4行目にあるので、skiprows=3として読み込む（エンコーディングはcp932を想定、必要に応じて変更）
        df = pd.read_csv(uploaded_file, skiprows=14, encoding='utf-8-sig')
        st.write("### アップロードされたデータ（一部）")
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
        st.stop()

    # -------------------------------
    # 日時項目の変換（文字列→datetime型）
    if '日時' in df.columns:
        try:
            df['日時'] = pd.to_datetime(df['日時'])
        except Exception as e:
            st.error(f"日時の変換エラー: {e}")
    
    # -------------------------------
    # 集計期間の指定（例：日付範囲でフィルタ）
    st.sidebar.header("2. 分析条件の設定")
    if '日時' in df.columns:
        min_date = df['日時'].min().date()
        max_date = df['日時'].max().date()
        start_date = st.sidebar.date_input("開始日", min_value=min_date, max_value=max_date, value=min_date)
        end_date   = st.sidebar.date_input("終了日", min_value=min_date, max_value=max_date, value=max_date)
        mask = (df['日時'].dt.date >= start_date) & (df['日時'].dt.date <= end_date)
        df_filtered = df.loc[mask].copy()
    else:
        df_filtered = df.copy()

    st.write("### 分析対象データ")
    st.dataframe(df_filtered.head())

    # -------------------------------
    # ① 期間別の行動頻度（対象行動ごとの回数集計）
    if '対象行動' in df_filtered.columns and '頻度' in df_filtered.columns:
        st.subheader("期間別の行動頻度")
        # 日付毎、または対象行動毎に集計
        df_filtered['日付'] = df_filtered['日時'].dt.date
        freq_df = df_filtered.groupby(['日付', '対象行動'])['頻度'].sum().reset_index()
        st.dataframe(freq_df.head())

        # グラフ描画（例: 折れ線グラフ）
    fig, ax = plt.subplots(figsize=(10, 5))
    for behavior in freq_df['対象行動'].unique():
        data = freq_df[freq_df['対象行動'] == behavior]
        ax.plot(data['日付'], data['頻度'], marker='o', label=behavior)

        ax.set_xlabel("日付")
        ax.set_ylabel("頻度")
        ax.set_title("日付別 行動頻度の推移")
        ax.legend()
        st.pyplot(fig)
        
        # -------------------------------
        # 介入フェーズ（またはその他フェーズ）の切替点があれば、垂直線で表示
        if 'フェーズ' in df_filtered.columns:
            # データを日時順にソートし、フェーズの切替点を抽出
            df_sorted = df_filtered.sort_values("日時")
            phase_boundaries = []
            previous_phase = df_sorted['フェーズ'].iloc[0]
            for idx, row in df_sorted.iterrows():
                current_phase = row['フェーズ']
                if current_phase != previous_phase:
                    phase_boundaries.append(row['日時'])
                    previous_phase = current_phase
            # グラフに境界線を描画
            for boundary in phase_boundaries:
                ax.axvline(boundary.date(), color='red', linestyle='--', alpha=0.7)
            st.write("※ 赤い破線はフェーズ切替点を示しています。")
        
        ax.set_xlabel("日付")
        ax.set_ylabel("頻度")
        ax.set_title("日付別 行動頻度の推移")
        ax.legend()
        st.pyplot(fig)
        st.write("""
**図の見方：**
- **横軸：** 日付  
- **縦軸：** 指定期間内の各対象行動の発生頻度の合計  
- 複数の線がそれぞれの対象行動を示し、線の上昇はその行動が頻発していることを意味します。  
- 赤い破線は、フェーズ（例：介入前→介入後）の切替点を表しています。
""")
    else:
        st.warning("『対象行動』および『頻度』の列が見つかりません。")

    # -------------------------------
    # ② 各対象行動の割合（全データに対する各行動の出現割合）
    if '対象行動' in df_filtered.columns:
        st.subheader("各対象行動の割合")
        behavior_counts = df_filtered['対象行動'].value_counts().reset_index()
        behavior_counts.columns = ['対象行動', '件数']
        st.dataframe(behavior_counts)

        # 円グラフ描画
        fig2, ax2 = plt.subplots(figsize=(6, 6))
        ax2.pie(behavior_counts['件数'], labels=behavior_counts['対象行動'], autopct='%1.1f%%', startangle=90)
        ax2.set_title("各対象行動の割合")
        st.pyplot(fig2)
        st.write("""
**図の見方：**
- 円グラフは、全体の記録に対して各対象行動が占める割合を示しています。  
- 各数値は、全体に対するパーセンテージです。
""")
    else:
        st.warning("『対象行動』の列が見つかりません。")

    # -------------------------------
    # ③ 強度に基づく簡易統計（例：平均強度など）
    if '強度' in df_filtered.columns:
        st.subheader("行動強度の統計")
        avg_intensity = df_filtered['強度'].mean()
        st.write(f"全体の平均強度： **{avg_intensity:.2f}**")
        st.write("※ 強度は1〜5など、事前に定めた尺度で評価してください。")
    else:
        st.info("『強度』の列が存在しないため、強度の統計は表示されません。")

    # -------------------------------
    # ④ 追加の定量データ（持続時間）の分析（あれば）
    if '持続時間' in df_filtered.columns:
        st.subheader("行動持続時間の統計")
        avg_duration = df_filtered['持続時間'].mean()
        total_duration = df_filtered['持続時間'].sum()
        st.write(f"全体の平均持続時間： **{avg_duration:.2f}** 分")
        st.write(f"全体の総持続時間： **{total_duration:.2f}** 分")
    else:
        st.info("『持続時間』の列が存在しないため、持続時間の統計は表示されません。")

    # -------------------------------
    # ⑤ 分析結果のサマリレポート作成とダウンロード
    st.markdown("---")
    st.subheader("分析結果レポート")
    report_lines = []
    report_lines.append("【応用行動分析 レポート】")
    report_lines.append(f"分析期間： {start_date} ～ {end_date}")
    report_lines.append("")
    if '対象行動' in df_filtered.columns and '頻度' in df_filtered.columns:
        overall_freq = df_filtered.groupby('対象行動')['頻度'].sum()
        report_lines.append("■ 対象行動別 総頻度")
        for behavior, freq in overall_freq.items():
            report_lines.append(f"  - {behavior} : {freq}")
    if '強度' in df_filtered.columns:
        report_lines.append("")
        report_lines.append(f"■ 全体の平均強度 : {avg_intensity:.2f}")
    if '持続時間' in df_filtered.columns:
        report_lines.append("")
        report_lines.append(f"■ 全体の平均持続時間 : {avg_duration:.2f} 単位")
        report_lines.append(f"■ 全体の総持続時間 : {total_duration:.2f} 単位")
    if 'フェーズ' in df_filtered.columns:
        report_lines.append("")
        report_lines.append("■ フェーズ別データ")
        phases = df_filtered['フェーズ'].unique()
        for phase in phases:
            phase_data = df_filtered[df_filtered['フェーズ'] == phase]
            phase_freq = phase_data['頻度'].sum() if '頻度' in phase_data.columns else None
            if '持続時間' in phase_data.columns:
                phase_duration = phase_data['持続時間'].mean()
            else:
                phase_duration = None
            report_lines.append(f"  - {phase}: 総頻度 = {phase_freq}, 平均持続時間 = {phase_duration if phase_duration is not None else 'N/A'}")
    
    report_text = "\n".join(report_lines)
    st.text_area("レポート内容（編集可）", report_text, height=250)
    
    st.download_button(
        label="レポートをダウンロード",
        data=report_text,
        file_name="aba_analysis_report.txt",
        mime="text/plain"
    )
else:
    st.info("サイドバーからCSVファイルをアップロードしてください。")
