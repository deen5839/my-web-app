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

# 3. 資料處理核心 (增加容錯解析)
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
                    data = json.load(f)
                    # 數據清洗：確保每一筆的日期格式在記憶體中都是乾淨的
                    for r in data:
                        r['date'] = self.clean_date(r['date'])
                    return data
            except:
                return []
        return []

    def clean_date(self, date_str):
        """處理舊載體中可能存在的不同日期格式"""
        try:
            # 嘗試長格式 (含時間)
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
        except:
            try:
                # 嘗試短格式 (僅日期)
                return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
            except:
                # 若都失敗，回傳今天
                return date.today().strftime('%Y-%m-%d')

    def save_data(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(st.session_state.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"存入載體失敗：{e}")

    def add_or_update_record(self, r_date, r_type, amount, category, note):
        date_str = r_date.strftime('%Y-%m-%d')
        if st.session_state.editing_id is not None:
            for r in st.session_state.records:
                if r['id'] == st.session_state.editing_id:
                    r['date'] = date_str
                    r['type'] = r_type
                    r['amount'] = amount
                    r['category'] = category
                    r['note'] = note
                    break
            st.session_state.editing_id = None
        else:
            new_id = 1 if not st.session_state.records else max(r['id'] for r in st.session_state.records) + 1
            record = {
                'id': new_id,
                'date': date_str,
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

tab1, tab2 = st.tabs(["➕ 帳務輸入/編輯", "📊 數據分析與管理"])

with tab1:
    edit_data = None
    if st.session_state.editing_id is not None:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        if edit_data:
            st.warning(f"⚠️ 正在編輯編號 #{st.session_state.editing_id}")

    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            # 安全讀取日期：如果解析失敗就給今天
            default_date = date.today()
            if edit_data:
                try:
                    default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
                except:
                    pass
            
            r_date = st.date_input("選擇日期", default_date)
            r_type = st.radio("性質", ["支出", "收入"], 
                            index=1 if edit_data and edit_data['type'] == "收入" else 0, 
                            horizontal=True)
            
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=100.0, 
                                   value=float(edit_data['amount']) if edit_data else 0.0)
        
        with col2:
            categories = ['飲食', '交通', '購物', '娛樂', '醫療', '其他'] if r_type == '支出' else ['薪水', '獎金', '投資', '其他']
            cat_idx = 0
            if edit_data and edit_data['category'] in categories:
                cat_idx = categories.index(edit_data['category'])
            
            category = st.selectbox("分類", categories, index=cat_idx)
            note = st.text_input("備註 (可選)", value=edit_data['note'] if edit_data else "")

        submitted = st.form_submit_button("🚀 存入載體", use_container_width=True)
        if submitted:
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.success("✅ 數據已更新！")
                st.rerun()
            else:
                st.error("❌ 金額不能為 0。")

    if st.session_state.editing_id is not None:
        if st.button("❌ 取消編輯"):
            st.session_state.editing_id = None
            st.rerun()

with tab2:
    if st.session_state.records:
        df = pd.DataFrame(st.session_state.records)
        df['amount'] = pd.to_numeric(df['amount'])
        
        inc = df[df['type'] == '收入']['amount'].sum()
        exp = df[df['type'] == '支出']['amount'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("總收入", f"${inc:,.0f}")
        c2.metric("總支出", f"${exp:,.0f}", delta=f"-{exp:,.0f}", delta_color="inverse")
        c3.metric("淨結餘", f"${inc - exp:,.0f}")
        
        st.write("### 📜 數據清單")
        for index, row in df.sort_values(by='date', ascending=False).iterrows():
            with st.container():
                d1, d2, d3, d4, d5 = st.columns([2, 2, 2, 3, 2])
                d1.write(f"📅 {row['date']}")
                d2.write(f"{row['type']}-{row['category']}")
                d3.write(f"${row['amount']:,.0f}")
                d4.write(f"{row['note']}")
                
                b1, b2 = d5.columns(2)
                if b1.button("✏️", key=f"e_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if b2.button("🗑️", key=f"d_{row['id']}"):
                    app.delete_record(row['id'])
                    st.rerun()
                st.divider()
    else:
        st.info("尚無數據。")

st.divider()
st.caption("AI 載體格式自動校正系統  🚀")
