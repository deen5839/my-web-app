import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date

# 1. 網頁初始設定
st.set_page_config(
    page_title="個人理財數據帳本", 
    page_icon="💰", 
    layout="wide"
)

# 2. 數據處理核心
class WebAccounting:
    def __init__(self):
        self.filename = 'accounting_data.json'
        # 確保 session_state 核心數據存在
        if 'records' not in st.session_state:
            st.session_state.records = self.load_data()
        if 'editing_id' not in st.session_state:
            st.session_state.editing_id = None

    def load_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_data(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(st.session_state.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"數據存入失敗：{e}")

    def add_or_update_record(self, r_date, r_type, amount, category, note):
        if st.session_state.editing_id is not None:
            for r in st.session_state.records:
                if r['id'] == st.session_state.editing_id:
                    r.update({
                        'date': r_date.strftime('%Y-%m-%d'),
                        'type': r_type,
                        'amount': amount,
                        'category': category,
                        'note': note
                    })
                    break
            st.session_state.editing_id = None
        else:
            new_id = 1 if not st.session_state.records else max(r['id'] for r in st.session_state.records) + 1
            record = {
                'id': new_id,
                'date': r_date.strftime('%Y-%m-%d'),
                'type': r_type,
                'amount': amount,
                'category': category,
                'note': note
            }
            st.session_state.records.append(record)
        self.save_data()

    def delete_record(self, r_id):
        st.session_state.records = [r for r in st.session_state.records if r['id'] != r_id]
        self.save_data()

# --- 重要：確保 app 實例在整份腳本中可被訪問 ---
if 'app_logic' not in st.session_state:
    st.session_state.app_logic = WebAccounting()
app = st.session_state.app_logic

# 3. 搜尋邏輯
search_query = st.query_params.get("q", "")

with st.sidebar:
    st.header("🔍 全域搜尋")
    def update_search():
        st.query_params["q"] = st.session_state.search_input
    
    new_q = st.text_input(
        "關鍵字搜尋", 
        value=search_query,
        key="search_input",
        on_change=update_search
    )

# 4. 數據準備
df = pd.DataFrame(st.session_state.records)
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    if new_q:
        df = df[df['note'].str.contains(new_q, na=False, case=False) | 
                df['category'].str.contains(new_q, na=False, case=False) |
                df['type'].str.contains(new_q, na=False, case=False)]

# 5. UI 介面
st.title("💰 個人理財：數據記錄帳本")

tab1, tab2, tab3 = st.tabs(["➕ 記帳與修正", "📊 數據分析", "📋 歷史清單"])

# --- Tab 1: 記帳 ---
with tab1:
    edit_data = None
    if st.session_state.editing_id is not None:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"🔧 正在編輯 ID #{st.session_state.editing_id}")

    # 使用 form 並給予 clear_on_submit=True 實現存檔後歸零
    # 注意：編輯模式下不宜自動清空，否則無法載入舊資料，所以 clear_on_submit 僅在非編輯時效果最好
    with st.form("accounting_form", clear_on_submit=(st.session_state.editing_id is None)):
        col1, col2 = st.columns(2)
        with col1:
            default_date = date.today()
            if edit_data:
                default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
            r_date = st.date_input("日期", default_date)
            r_type = st.radio("類型", ["支出", "收入"], index=0 if not edit_data or edit_data['type']=="支出" else 1, horizontal=True)
            
        with col2:
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=10.0, value=float(edit_data['amount']) if edit_data else 0.0)
            categories = ['薪水', '獎金', '投資', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '娛樂', '醫療', '其他']
            cat_idx = 0
            if edit_data and edit_data['category'] in categories:
                cat_idx = categories.index(edit_data['category'])
            category = st.selectbox("分類", categories, index=cat_idx)

        note = st.text_input("備註內容", value=edit_data['note'] if edit_data else "")
        submit_btn = st.form_submit_button("🚀 儲存紀錄", use_container_width=True)
        
        if submit_btn:
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.success("數據已儲存！")
                st.rerun()

# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        expense_df = df[df['type'] == '支出']
        income_val = df[df['type'] == '收入']['amount'].sum()
        expense_val = expense_df['amount'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("總收入", f"${income_val:,.0f}")
        c2.metric("總支出", f"${expense_val:,.0f}")
        c3.metric("淨餘額", f"${income_val - expense_val:,.0f}")
        
        st.subheader("📊 支出分類比例")
        if not expense_df.empty:
            # 解決亂跑問題：先彙整數據再繪圖，並固定寬度
            chart_data = expense_df.groupby('category')['amount'].sum()
            st.bar_chart(chart_data, use_container_width=True)
        else:
            st.info("暫無支出數據。")
    else:
        st.info("尚無數據。")

# --- Tab 3: 歷史清單 ---
with tab3:
    if not df.empty:
        if st.session_state.editing_id:
            if st.button("取消編輯"):
                st.session_state.editing_id = None
                st.rerun()

        # 為了防止刪除時索引跑掉，我們遍歷 dataframe
        for _, row in df.sort_values(by=['date'], ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"備註: {row['note']}")
                ec1, ec2 = st.columns(2)
                # 使用唯一 key 避免衝突
                if ec1.button("✏️ 編輯", key=f"edit_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if ec2.button("🗑️ 刪除", key=f"del_{row['id']}"):
                    app.delete_record(row['id'])
                    st.rerun()
    else:
        st.warning("清單為空。")
