import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date

# 1. 網頁初始設定
st.set_page_config(
    page_title="個人理財數據檔案", 
    page_icon="💰", 
    layout="wide"
)

# 2. 強力 CSS 注入 (讓介面變漂亮，且隱藏那些多餘的按鈕)
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

# 3. 資料處理核心 (WebAccounting Class)
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
            st.error(f"數據存入檔案失敗：{e}")

    def add_or_update_record(self, r_date, r_type, amount, category, note):
        if st.session_state.editing_id is not None:
            # 編輯邏輯
            for r in st.session_state.records:
                if r['id'] == st.session_state.editing_id:
                    r['date'] = r_date.strftime('%Y-%m-%d')
                    r['type'] = r_type
                    r['amount'] = amount
                    r['category'] = category
                    r['note'] = note
                    break
            st.session_state.editing_id = None
        else:
            # 新增邏輯
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

# 初始化 App
app = WebAccounting()

# 4. 網頁 UI 呈現
st.title("💰 個人理財：數據記錄帳本")
st.write(f"系統狀態：穩定運行中 | 慶祝 12/12 康復回歸 ✨")

tab1, tab2 = st.tabs(["➕ 記帳與修正", "📊 數據清單與分析"])

# --- Tab 1: 新增或編輯 ---
with tab1:
    edit_data = None
    if st.session_state.editing_id is not None:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"正在編輯 ID #{st.session_state.editing_id} 的紀錄")

    # 使用 Form 確保輸入資料完整後再發送
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # 日期手動選擇功能
            default_date = date.today()
            if edit_data:
                default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
            r_date = st.date_input("選擇日期", default_date)
            
            r_type_idx = 0
            if edit_data and edit_data['type'] == "收入": r_type_idx = 1
            r_type = st.radio("收支類型", ["支出", "收入"], index=r_type_idx, horizontal=True)
            
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
            note = st.text_input("備註內容", value=default_note)

        # 提交按鈕
        submit_label = "🚀 更新紀錄" if st.session_state.editing_id else "🚀 存入載體"
        if st.form_submit_button(submit_label, use_container_width=True):
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.success("數據已寫入晶片！")
                st.rerun()
            else:
                st.error("金額必須大於零。")

    if st.session_state.editing_id is not None:
        if st.button("❌ 放棄編輯"):
            st.session_state.editing_id = None
            st.rerun()

# --- Tab 2: 分析與明細 ---
with tab2:
    if st.session_state.records:
        df = pd.DataFrame(st.session_state.records)
        df['amount'] = df['amount'].astype(float)
        
        income = df[df['type'] == '收入']['amount'].sum()
        expense = df[df['type'] == '支出']['amount'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("總收入", f"${income:,.0f}")
        c2.metric("總支出", f"${expense:,.0f}")
        c3.metric("淨資產", f"${income - expense:,.0f}")
        
        st.divider()
        st.write("### 📜 交易歷史明細")
        
        # 逆序排列（新的在前）並提供編輯/刪除按鈕
        for index, row in df.sort_values(by='date', ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"備註：{row['note']}")
                btn_c1, btn_c2 = st.columns(2)
                if btn_c1.button("✏️ 修改這筆", key=f"edit_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if btn_c2.button("🗑️ 刪除紀錄", key=f"del_{row['id']}"):
                    app.delete_record(row['id'])
                    st.rerun()
        
        if expense > 0:
            st.write("### 📊 支出分佈圖")
            st.bar_chart(df[df['type'] == '支出'].groupby('category')['amount'].sum())
    else:
        st.info("目前檔案空空如也，請先輸入帳務。")

st.divider()
st.caption("AI 載體穩定運作中  (2025/12/12) 🚀")
