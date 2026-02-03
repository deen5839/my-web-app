import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date

# 1. 網頁配置：確保手機版畫面不縮放、不亂跑
st.set_page_config(
    page_title="理財數據帳本 Pro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. 修正後的樣式表 (解決 TypeError)
st.markdown("""
    <style>
    /* 強化手機端 Tab 的點擊面積與穩定度 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #f8f9fa;
        border-radius: 8px 8px 0px 0px;
        padding: 8px 12px;
        font-weight: 600;
    }
    /* 避免手機滑動時圖表高度閃爍 */
    [data-testid="stVerticalBlock"] > div {
        max-width: 100%;
    }
    /* 按鈕美化 */
    .stButton>button {
        border-radius: 10px;
        height: 3em;
        transition: all 0.3s;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 核心數據架構 (伺服器底層邏輯)
class FinancialKernel:
    def __init__(self):
        self.db_path = 'financial_vault.json'
        if 'vault' not in st.session_state:
            st.session_state.vault = self._load_vault()
    
    def _load_vault(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def commit(self):
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.vault, f, ensure_ascii=False, indent=2)

    def add_entry(self, entry_date, entry_type, amount, category, note):
        new_id = datetime.now().strftime('%Y%m%d%H%M%S')
        data = {
            "id": new_id,
            "date": entry_date.strftime('%Y-%m-%d'),
            "type": entry_type,
            "amount": float(amount),
            "category": category,
            "note": note
        }
        st.session_state.vault.append(data)
        self.commit()

    def remove_entry(self, entry_id):
        st.session_state.vault = [e for e in st.session_state.vault if e['id'] != entry_id]
        self.commit()

kernel = FinancialKernel()

# 4. 介面標題
st.title("💰 理財數據帳本 Pro")
if st.session_state.vault:
    df = pd.DataFrame(st.session_state.vault)
    df['date'] = pd.to_datetime(df['date'])
    
    # 頂部快取指標
    income = df[df['type'] == '收入']['amount'].sum()
    expense = df[df['type'] == '支出']['amount'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("總收入", f"${income:,.0f}")
    c2.metric("總支出", f"${expense:,.0f}", delta=f"-{expense:,.0f}", delta_color="inverse")
    c3.metric("淨資產", f"${income - expense:,.0f}")
else:
    df = pd.DataFrame()
    st.info("帳本目前無數據，請開始記錄。")

st.divider()

# 5. 功能分頁 (比照最成功版本)
tab_add, tab_chart, tab_list = st.tabs(["📝 快速輸入", "📊 數據分析", "📜 歷史明細"])

with tab_add:
    # 使用 form 確保數據完整提交且自動歸零
    with st.form("entry_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            in_date = st.date_input("交易日期", date.today())
            in_type = st.segmented_control("類型", ["支出", "收入"], default="支出")
        with col_b:
            in_amount = st.number_input("金額 (NTD)", min_value=0.0, step=10.0)
            options = ['飲食', '交通', '購物', '醫療', '娛樂', '其他'] if in_type == "支出" else ['薪資', '獎金', '投資', '其他']
            in_cat = st.selectbox("分類", options)
            
        in_note = st.text_input("備註 (選填)")
        
        submit = st.form_submit_button("寫入帳本", use_container_width=True)
        
        if submit:
            if in_amount > 0:
                kernel.add_entry(in_date, in_type, in_amount, in_cat, in_note)
                st.success("數據寫入成功！")
                st.rerun()
            else:
                st.error("金額不可為零")

with tab_chart:
    if not df.empty:
        # 分類支出統計
        st.subheader("支出分佈")
        exp_df = df[df['type'] == '支出']
        if not exp_df.empty:
            cat_sum = exp_df.groupby('category')['amount'].sum().reset_index()
            # 使用橫向條形圖，在手機上讀取最直覺
            st.bar_chart(cat_sum.set_index('category'), horizontal=True)
        
        st.divider()
        st.subheader("收支趨勢")
        trend = df.pivot_table(index='date', columns='type', values='amount', aggfunc='sum').fillna(0)
        st.line_chart(trend)
    else:
        st.write("尚無數據可供分析")

with tab_list:
    if not df.empty:
        # 顯示最近 10 筆紀錄
        sorted_df = df.sort_values(by='date', ascending=False)
        for _, row in sorted_df.iterrows():
            with st.expander(f"📅 {row['date'].strftime('%m/%d')} | {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"類型：{row['type']}")
                st.write(f"備註：{row['note'] if row['note'] else '無'}")
                if st.button("🗑️ 刪除紀錄", key=f"del_{row['id']}"):
                    kernel.remove_entry(row['id'])
                    st.rerun()
    else:
        st.write("清單空空如也")

# 頁尾提示
st.markdown("---")
st.caption(f"數據帳本狀態：穩定運行中 | 現在時間：{datetime.now().strftime('%H:%M')}")
