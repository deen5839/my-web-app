import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date
import io

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
            except: return []
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
            st.session_state.records.append({
                'id': new_id,
                'date': r_date.strftime('%Y-%m-%d'),
                'type': r_type,
                'amount': amount,
                'category': category,
                'note': note
            })
        self.save_data()

if 'app' not in st.session_state:
    st.session_state.app = WebAccounting()
app = st.session_state.app

# 3. 側邊欄：搜尋與 Excel 備份
with st.sidebar:
    st.header("🔍 數據管理")
    search_query = st.text_input("關鍵字搜尋", placeholder="搜尋備註或分類...", key="sidebar_search")
    
    st.divider()
    st.header("📊 檔案導出")
    
    if st.session_state.records:
        # 將資料轉為 DataFrame
        export_df = pd.DataFrame(st.session_state.records)
        # 調整欄位順序與名稱，讓 Excel 看起來更整齊
        export_df = export_df[['date', 'type', 'category', 'amount', 'note']]
        export_df.columns = ['日期', '收支類型', '分類', '金額', '備註']
        
        # 製作 Excel 二進位流
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='記帳明細')
            # 這裡可以自動調整欄寬 (選配)
        
        st.download_button(
            label="📥 下載 Excel 備份檔",
            data=buffer.getvalue(),
            file_name=f"理財記錄_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.info("尚無數據可導出")
    
    st.info("💡 下載後可用 Excel 或 Google 試算表開啟。")

# 4. 數據預處理 (過濾搜尋結果)
df = pd.DataFrame(st.session_state.records)
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    if search_query:
        df = df[
            df['note'].str.contains(search_query, na=False, case=False) | 
            df['category'].str.contains(search_query, na=False, case=False)
        ]

# 5. UI 主介面
st.title("💰 個人理財：數據記錄帳本")
tab1, tab2, tab3 = st.tabs(["➕ 記帳與修正", "📊 數據分析", "📋 歷史清單"])

# --- Tab 1: 記帳 ---
with tab1:
    edit_data = None
    if st.session_state.editing_id:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"🔧 正在編輯 ID #{st.session_state.editing_id}")

    default_type_idx = 0 if not edit_data or edit_data['type'] == "支出" else 1
    r_type = st.radio("收支類型", ["支出", "收入"], index=default_type_idx, horizontal=True, key="main_type_radio")

    with st.form("input_form", clear_on_submit=(st.session_state.editing_id is None)):
        col1, col2 = st.columns(2)
        with col1:
            default_date = date.today()
            if edit_data:
                default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
            r_date = st.date_input("日期", default_date)
            
        with col2:
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=10.0, value=float(edit_data['amount']) if edit_data else 0.0)
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
                st.success("數據已存檔！欄位已清空。")
                st.rerun()

# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        inc = df[df['type'] == '收入']['amount'].sum()
        exp = df[df['type'] == '支出']['amount'].sum()
        c1.metric("搜尋結果收入", f"${inc:,.0f}")
        c2.metric("搜尋結果支出", f"${exp:,.0f}")
        c3.metric("餘額", f"${inc-exp:,.0f}")
        
        st.divider()
        st.subheader("📌 支出佔比分析")
        exp_data = df[df['type'] == '支出'].groupby('category')['amount'].sum()
        if not exp_data.empty:
            st.bar_chart(exp_data, use_container_width=True)
        else:
            st.info("尚無支出數據。")
    else:
        st.info("沒有數據。")

# --- Tab 3: 歷史清單 ---
with tab3:
    if not df.empty:
        if st.session_state.editing_id:
            if st.button("❌ 取消編輯模式"):
                st.session_state.editing_id = None
                st.rerun()

        for _, row in df.sort_values(by='date', ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"備註: {row['note']}")
                ec1, ec2 = st.columns(2)
                if ec1.button("✏️ 編輯", key=f"edit_btn_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if ec2.button("🗑️ 刪除", key=f"del_btn_{row['id']}"):
                    st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                    app.save_data()
                    st.rerun()
    else:
        st.warning("清單為空。")
