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

app = WebAccounting()

# --- 搜尋邏輯 ---
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
    st.divider()
    st.info("💡 系統已優化：存檔後將自動重置輸入欄位。")

# 5. 網頁 UI
st.title("💰 個人理財：數據記錄帳本")

tab1, tab2, tab3 = st.tabs(["➕ 記帳與修正", "📊 數據分析", "📋 歷史清單"])

# 數據轉換
df = pd.DataFrame(st.session_state.records)
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    if new_q:
        df = df[df['note'].str.contains(new_q, na=False, case=False) | 
                df['category'].str.contains(new_q, na=False, case=False)]

# --- Tab 1: 記帳 ---
with tab1:
    edit_data = None
    if st.session_state.editing_id is not None:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"🔧 正在編輯 ID #{st.session_state.editing_id}")

    # 使用 Form 來處理歸零邏輯
    with st.form("accounting_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            default_date = date.today()
            if edit_data:
                default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
            r_date = st.date_input("日期", default_date)
            r_type = st.radio("類型", ["支出", "收入"], index=0 if not edit_data or edit_data['type']=="支出" else 1, horizontal=True)
            
        with col2:
            # 這裡的 value 只有在編輯模式下才固定
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
                st.success("數據儲存成功！欄位已重置。")
                st.rerun()
            else:
                st.error("金額必須大於 0")

# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        # 數據計算
        income = df[df['type'] == '收入']['amount'].sum()
        expense = df[df['type'] == '支出']['amount'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("總收入", f"${income:,.0f}")
        c2.metric("總支出", f"${expense:,.0f}")
        c3.metric("淨餘額", f"${income - expense:,.0f}")
        
        st.divider()
        st.subheader("📌 分類支出佔比")
        
        # 修復跑版問題：使用容器寬度並將圖表資料處理好
        expense_df = df[df['type'] == '支出'].groupby('category')['amount'].sum().reset_index()
        if not expense_df.empty:
            # 使用更穩定的 bar_chart 並強制使用容器寬度
            st.bar_chart(expense_df.set_index('category'), use_container_width=True)
        else:
            st.info("尚無支出數據可供分析。")
    else:
        st.info("請先到記帳分頁輸入數據。")

# --- Tab 3: 歷史清單 ---
with tab3:
    if not df.empty:
        # 增加一個「取消編輯」按鈕，如果正在編輯中
        if st.session_state.editing_id:
            if st.button("❌ 取消編輯模式"):
                st.session_state.editing_id = None
                st.rerun()

        for index, row in df.sort_values(by=['date'], ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"備註: {row['note']}")
                ec1, ec2 = st.columns(2)
                if ec1.button("✏️ 編輯", key=f"e_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if ec2.button("🗑️ 刪除", key=f"d_{row['id']}"):
                    app.delete_record(row['id'])
                    st.rerun()
    else:
        st.warning("清單為空。")
