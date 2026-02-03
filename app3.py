import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date
import io

# 1. 網頁初始設定
st.set_page_config(
    page_title="理財數據帳本 - 專業版", 
    page_icon="💰", 
    layout="wide"
)

# 2. 數據處理核心 (加入防錯機制)
class WebAccounting:
    def __init__(self):
        self.filename = 'accounting_data.json'
        # 確保所有必要的狀態都已初始化
        if 'records' not in st.session_state:
            st.session_state.records = self.load_data()
        if 'editing_id' not in st.session_state:
            st.session_state.editing_id = None

    def load_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
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
            st.session_state.records.append({
                'id': new_id,
                'date': r_date.strftime('%Y-%m-%d'),
                'type': r_type,
                'amount': amount,
                'category': category,
                'note': note
            })
        self.save_data()

# 初始化 App
if 'app' not in st.session_state:
    st.session_state.app = WebAccounting()
app = st.session_state.app

# 3. 側邊欄：搜尋、Excel 備份與開發者資訊
with st.sidebar:
    st.header("🔍 數據管理")
    search_query = st.text_input("關鍵字搜尋", placeholder="搜尋備註或分類...", key="sidebar_search")
    
    st.divider()
    st.header("📊 檔案導出")
    if st.session_state.records:
        export_df = pd.DataFrame(st.session_state.records)
        export_df = export_df[['date', 'type', 'category', 'amount', 'note']]
        export_df.columns = ['日期', '收支類型', '分類', '金額', '備註']
        
        buffer = io.BytesIO()
        # 使用 openpyxl 確保免安裝 xlsxwriter 也能運作
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='記帳明細')
        
        st.download_button(
            label="📥 下載 Excel 備份檔",
            data=buffer.getvalue(),
            file_name=f"理財記錄_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    st.divider()
    st.markdown("### 👨‍💻 開發者資訊")
    st.info("本系統由 **Python 數據帳本工作組** 開發，專為提升個人理財效率設計。")
    st.caption("版本：v1.1 (Plus 優化版)")

# 4. 數據預處理
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
tab1, tab2, tab3 = st.tabs(["➕ 快速記帳", "📊 數據分析", "📋 歷史清單"])

# --- Tab 1: 記帳 ---
with tab1:
    edit_data = None
    if st.session_state.editing_id:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"🔧 正在編輯模式...")

    r_type = st.radio("收支類型", ["支出", "收入"], index=0 if not edit_data or edit_data['type'] == "支出" else 1, horizontal=True)

    with st.form("input_form", clear_on_submit=(st.session_state.editing_id is None)):
        col1, col2 = st.columns(2)
        with col1:
            default_date = date.today()
            if edit_data:
                default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
            r_date = st.date_input("日期", default_date)
            
        with col2:
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=10.0, value=float(edit_data['amount']) if edit_data else 0.0)
            categories = ['薪水', '獎金', '投資', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '娛樂', '醫療', '其他']
            cat_idx = 0
            if edit_data and edit_data['category'] in categories:
                cat_idx = categories.index(edit_data['category'])
            category = st.selectbox("分類標籤", categories, index=cat_idx)

        note = st.text_input("備註內容", value=edit_data['note'] if edit_data else "", placeholder="例如：午餐、停車費...")
        submit_btn = st.form_submit_button("🚀 儲存紀錄", use_container_width=True)
        
        if submit_btn:
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.success("數據存檔成功！")
                st.rerun()

# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        inc = df[df['type'] == '收入']['amount'].sum()
        exp = df[df['type'] == '支出']['amount'].sum()
        c1.metric("搜尋結果收入", f"${inc:,.0f}")
        c2.metric("搜尋結果支出", f"${exp:,.0f}")
        c3.metric("本期結餘", f"${inc-exp:,.0f}", delta=f"{inc-exp:,.0f}")
        
        st.divider()
        st.subheader("📌 支出結構圖")
        exp_data = df[df['type'] == '支出'].groupby('category')['amount'].sum()
        if not exp_data.empty:
            st.bar_chart(exp_data, use_container_width=True)
        else:
            st.info("尚無支出數據可供分析。")
    else:
        st.info("👋 歡迎使用！請先到第一頁記下一筆帳目吧。")

# --- Tab 3: 歷史清單 ---
with tab3:
    if not df.empty:
        if st.session_state.editing_id:
            if st.button("❌ 放棄修改"):
                st.session_state.editing_id = None
                st.rerun()

        for _, row in df.sort_values(by=['date', 'id'], ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"📝 備註: {row['note'] if row['note'] else '無'}")
                ec1, ec2 = st.columns(2)
                if ec1.button("✏️ 修改", key=f"edit_btn_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if ec2.button("🗑️ 刪除", key=f"del_btn_{row['id']}"):
                    st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                    app.save_data()
                    st.rerun()
    else:
        st.warning("清單是空的喔！")
