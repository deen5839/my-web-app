import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date

# 1. 網頁初始設定
st.set_page_config(page_title="個人理財數據帳本", page_icon="💰", layout="wide")

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
            except: return []
        return []

    def save_data(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.records, f, ensure_ascii=False, indent=2)

    def add_or_update_record(self, r_date, r_type, amount, category, note):
        if st.session_state.editing_id is not None:
            for r in st.session_state.records:
                if r['id'] == st.session_state.editing_id:
                    r.update({'date': r_date.strftime('%Y-%m-%d'), 'type': r_type, 'amount': amount, 'category': category, 'note': note})
                    break
            st.session_state.editing_id = None
        else:
            new_id = 1 if not st.session_state.records else max(r['id'] for r in st.session_state.records) + 1
            st.session_state.records.append({'id': new_id, 'date': r_date.strftime('%Y-%m-%d'), 'type': r_type, 'amount': amount, 'category': category, 'note': note})
        self.save_data()

# 初始化 App
if 'app' not in st.session_state:
    st.session_state.app = WebAccounting()
app = st.session_state.app

# --- Tab 1: 記帳 (核心修復區) ---
st.title("💰 個人理財：數據記錄帳本")
tab1, tab2, tab3 = st.tabs(["➕ 記帳與修正", "📊 數據分析", "📋 歷史清單"])

with tab1:
    # 取得編輯資料
    edit_data = None
    if st.session_state.editing_id:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"🔧 編輯模式：ID #{st.session_state.editing_id}")

    # --- 關鍵修正：將類型選單放在 Form 外面，確保連動反應 ---
    col_t1, col_t2 = st.columns([1, 1])
    with col_t1:
        # 使用 Session State 來控管類型，確保切換時立刻觸發畫面重繪
        default_type_idx = 0 if not edit_data or edit_data['type'] == "支出" else 1
        r_type = st.radio("收支類型", ["支出", "收入"], index=default_type_idx, horizontal=True, key="type_selector")

    with st.form("accounting_form", clear_on_submit=(st.session_state.editing_id is None)):
        col1, col2 = st.columns(2)
        with col1:
            default_date = date.today()
            if edit_data:
                default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
            r_date = st.date_input("日期", default_date)
            
        with col2:
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=10.0, value=float(edit_data['amount']) if edit_data else 0.0)
            
            # 根據 Form 外的 r_type 動態決定選單
            if r_type == '收入':
                categories = ['薪水', '獎金', '投資', '其他']
            else:
                categories = ['飲食', '交通', '購物', '娛樂', '醫療', '其他']
            
            cat_idx = 0
            if edit_data and edit_data['category'] in categories:
                cat_idx = categories.index(edit_data['category'])
            category = st.selectbox("分類標籤", categories, index=cat_idx)

        note = st.text_input("備註內容", value=edit_data['note'] if edit_data else "")
        submit_btn = st.form_submit_button("🚀 儲存紀錄", use_container_width=True)
        
        if submit_btn:
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.success("存檔成功！欄位已重置。")
                st.rerun()
            else:
                st.error("請輸入正確金額")

# --- Tab 2 & 3 (保持簡潔穩定) ---
df = pd.DataFrame(st.session_state.records)
with tab2:
    if not df.empty:
        df['amount'] = pd.to_numeric(df['amount'])
        c1, c2, c3 = st.columns(3)
        inc = df[df['type'] == '收入']['amount'].sum()
        exp = df[df['type'] == '支出']['amount'].sum()
        c1.metric("總收入", f"${inc:,.0f}")
        c2.metric("總支出", f"${exp:,.0f}")
        c3.metric("淨額", f"${inc-exp:,.0f}")
        
        st.subheader("📊 分類支出圖表")
        exp_df = df[df['type'] == '支出'].groupby('category')['amount'].sum()
        if not exp_df.empty:
            st.bar_chart(exp_df, use_container_width=True) # 強制容器寬度，防止滑動跑版
    else:
        st.info("尚無數據")

with tab3:
    if not df.empty:
        if st.session_state.editing_id:
            if st.button("取消編輯"):
                st.session_state.editing_id = None
                st.rerun()
        for _, row in df.sort_values(by='date', ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - {row['category']} | ${row['amount']:,.0f}"):
                c1, c2 = st.columns(2)
                if c1.button("✏️", key=f"e_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if c2.button("🗑️", key=f"d_{row['id']}"):
                    st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                    app.save_data()
                    st.rerun()
