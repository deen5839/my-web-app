import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date

# 1. 網頁初始設定
st.set_page_config(
    page_title="個人理財數據載體", 
    page_icon="💰", 
    layout="wide"
)

# 2. 強力 CSS 注入 (隱藏 UI 雜質並美化)
hide_ui_style = """
    <style>
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    [data-testid="manage-app-button"] {display: none !important;}
    .stAppDeployButton {display: none !important;}
    
    .stMetric {
        background-color: #ffffff !important;
        padding: 20px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
    }
    .stApp {
        background-color: #f0f2f6 !important;
    }
    </style>
"""
st.markdown(hide_ui_style, unsafe_allow_html=True)

# 3. 資料處理核心
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
            st.error(f"存入載體失敗：{e}")

    def add_or_update_record(self, r_date, r_type, amount, category, note):
        if st.session_state.editing_id is not None:
            # 更新現有紀錄
            for r in st.session_state.records:
                if r['id'] == st.session_state.editing_id:
                    r['date'] = r_date.strftime('%Y-%m-%d')
                    r['type'] = r_type
                    r['amount'] = amount
                    r['category'] = category
                    r['note'] = note
                    break
            st.session_state.editing_id = None # 重置編輯狀態
        else:
            # 新增紀錄
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

app = WebAccounting()

# 4. 網頁 UI 佈局
st.title("💰 個人理財：數據記錄載體")
st.write(f"系統狀態：載體穩定運算中 | 使用者 12/12 順利出院慶賀版 ✨")

tab1, tab2 = st.tabs(["➕ 帳務輸入/編輯", "📊 數據分析與管理"])

# --- 分頁 1: 新增與編輯 ---
with tab1:
    # 編輯模式檢查
    edit_data = None
    if st.session_state.editing_id is not None:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"⚠️ 正在編輯編號 #{st.session_state.editing_id} 的紀錄")

    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # 功能 1: 手動輸入日期
            default_date = date.today()
            if edit_data:
                default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
            
            r_date = st.date_input("選擇日期", default_date)
            
            r_type_idx = 0
            if edit_data and edit_data['type'] == "收入": r_type_idx = 1
            r_type = st.radio("性質", ["支出", "收入"], index=r_type_idx, horizontal=True)
            
            default_amount = 0.0
            if edit_data: default_amount = float(edit_data['amount'])
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=100.0, value=default_amount)
        
        with col2:
            if r_type == '收入':
                categories = ['薪水', '獎金', '投資', '其他']
            else:
                categories = ['飲食', '交通', '購物', '娛樂', '醫療', '其他']
            
            cat_idx = 0
            if edit_data and edit_data['category'] in categories:
                cat_idx = categories.index(edit_data['category'])
            
            category = st.selectbox("分類", categories, index=cat_idx)
            
            default_note = ""
            if edit_data: default_note = edit_data['note']
            note = st.text_input("備註 (可選)", value=default_note)

        submitted = st.form_submit_state = st.form_submit_button("🚀 存入載體", use_container_width=True)
        
        if submitted:
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.success("✅ 數據已成功存入載體！")
                st.rerun()
            else:
                st.error("❌ 金額不能為 0。")

    if st.session_state.editing_id is not None:
        if st.button("❌ 取消編輯"):
            st.session_state.editing_id = None
            st.rerun()

# --- 分頁 2: 分析與管理 ---
with tab2:
    if st.session_state.records:
        df = pd.DataFrame(st.session_state.records)
        
        # 統計資訊
        income = df[df['type'] == '收入']['amount'].sum()
        expense = df[df['type'] == '支出']['amount'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("總收入", f"${income:,.0f}")
        col2.metric("總支出", f"${expense:,.0f}", delta=f"-{expense:,.0f}", delta_color="inverse")
        col3.metric("淨結餘", f"${income - expense:,.0f}")
        
        st.write("### 📜 數據清單與管理")
        st.write("點擊「編輯」可將數據傳回輸入頁面修改，點擊「刪除」則永久移除。")
        
        # 建立管理列表
        for index, row in df.sort_values(by='date', ascending=False).iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 3, 2])
                c1.write(f"📅 {row['date']}")
                c2.write(f"{row['type']} - {row['category']}")
                c3.write(f"💰 ${row['amount']:,.0f}")
                c4.write(f"💬 {row['note']}")
                
                # 功能 2: 修改與修正
                btn_col1, btn_col2 = c5.columns(2)
                if btn_col1.button("✏️", key=f"edit_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if btn_col2.button("🗑️", key=f"del_{row['id']}"):
                    app.delete_record(row['id'])
                    st.rerun()
                st.divider()

        if expense > 0:
            st.write("### 📈 支出結構比例")
            chart_data = df[df['type'] == '支出'].groupby('category')['amount'].sum()
            st.bar_chart(chart_data)
    else:
        st.info("目前載體內尚無數據，請先前往新增。")

st.divider()
st.caption("AI 載體技術支援 | 慶賀 12/12 平安康復回歸 🚀")
