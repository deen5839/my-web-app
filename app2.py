import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

# 1. 網頁初始設定
st.set_page_config(page_title="個人理財載體", page_icon="💰", layout="wide")

# 2. 強力 CSS 注入
hide_ui_style = """
    <style>
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    [data-testid="manage-app-button"] {display: none !important;}
    .stAppDeployButton {display: none !important;}
    </style>
"""
st.markdown(hide_ui_style, unsafe_allow_html=True)
# 3. 資料處理中心
class WebAccounting:
    def __init__(self):
        self.filename = 'accounting_data.json'
        if 'records' not in st.session_state:
            st.session_state.records = self.load_data()

    def load_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_data(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.records, f, ensure_ascii=False, indent=2)

    def add_record(self, r_type, amount, category, note):
        new_id = 1 if not st.session_state.records else max(r['id'] for r in st.session_state.records) + 1
        record = {
            'id': new_id,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
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

# 4. 網頁 UI
st.title("💰 個人理財：數據記錄載體")

tab1, tab2 = st.tabs(["✨ 新增流水", "📊 數據分析"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        r_type = st.radio("選擇性質", ["支出", "收入"], horizontal=True)
        amount = st.number_input("輸入金額", min_value=0.0, step=10.0)
    with col2:
        category = st.selectbox("分類", ['飲食', '交通', '購物', '娛樂', '醫療', '其他'])
        note = st.text_input("備註")
    
    if st.button("🚀 存入載體", use_container_width=True):
        if amount > 0:
            app.add_record(r_type, amount, category, note)
            st.success("紀錄成功！")
            st.rerun()

with tab2:
    if st.session_state.records:
        df = pd.DataFrame(st.session_state.records)
        st.dataframe(df, use_container_width=True)
        # 簡單統計
        expense = df[df['type'] == '支出']['amount'].sum()
        st.metric("總支出", f"${expense:,.0f}")
    else:
        st.info("尚無數據")
