import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date, timedelta
import io
import uuid
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# 1. 網頁初始設定
st.set_page_config(
    page_title="個人理財數據帳本", 
    page_icon="💰", 
    layout="wide"
)

# 2. 數據處理核心 (加入 ChatGPT 文件建議的初始化保險)
class WebAccounting:
    def __init__(self):
        self.sheet_url = "https://docs.google.com/spreadsheets/d/1wc7rLawk5i6gfMEFw8p9hK_gUFlUIvCuL6-FPETNsw8/edit"
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            st.error(f"❌ 雲端連接初始化失敗: {e}")
        
        # 💡 強制初始化必要的 session_state，防止 AttributeError
        if 'records' not in st.session_state:
            st.session_state.records = self.load_data()
        if 'editing_id' not in st.session_state:
            st.session_state.editing_id = None

    def load_data(self):
        try:
            # 加上 ttl=0 強迫抓取最新數據
            df = self.conn.read(spreadsheet=self.sheet_url, worksheet="Sheet1", ttl=0)
            if df is not None and not df.empty:
                return df.to_dict('records')
        except:
            pass
        return []

    def save_data(self):
        """同步數據至雲端"""
        try:
            if not st.session_state.records:
                df = pd.DataFrame(columns=['id', 'date', 'type', 'amount', 'category', 'note'])
            else:
                df = pd.DataFrame(st.session_state.records)
            
            st.cache_data.clear()
            self.conn.update(spreadsheet=self.sheet_url, worksheet="Sheet1", data=df)
            st.cache_data.clear()
            st.toast("✅ 雲端同步成功！", icon="☁️")
            return True
        except Exception as e:
            # 雖然失敗，但我們安靜處理，讓網頁不崩潰
            st.sidebar.error(f"⚠️ 雲端寫入攔截：{e}")
            return False

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
            new_id = str(uuid.uuid4())[:8]
            st.session_state.records.append({
                'id': new_id, 'date': r_date.strftime('%Y-%m-%d'),
                'type': r_type, 'amount': amount, 'category': category, 'note': note
            })
        self.save_data()

# --- 初始化應用實例 ---
if 'app' not in st.session_state:
    st.session_state.app = WebAccounting()

# 💡 二次保險：確保變數絕對存在
if 'editing_id' not in st.session_state:
    st.session_state.editing_id = None
if 'records' not in st.session_state:
    st.session_state.records = []

app = st.session_state.app

# 3. 側邊欄：搜尋與 Excel 備份
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
        try:
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='記帳明細')
            
            st.download_button(
                label="📥 下載 Excel 備份檔",
                data=buffer.getvalue(),
                file_name=f"理財記錄_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except:
            st.error("Excel 產生失敗")
    else:
        st.info("尚無數據可導出")

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

# 台灣時區招呼語
taiwan_now = datetime.now() + timedelta(hours=8)
now_hour = taiwan_now.hour

if 5 <= now_hour < 12:
    greeting = "🌅 早上好！今天也是充滿數據力的一天。"
elif 12 <= now_hour < 18:
    greeting = "☀️ 下午好！小口喝水，保持喉嚨濕潤喔。"
else:
    greeting = "🌙 晚上好！辛苦了，早點休息。"

st.info(f"{greeting}")
st.caption(f"🚀 雲端版 v1.3 | 系統時間：{taiwan_now.strftime('%H:%M')} | 數據載體：Google Sheets")
st.divider()

tab1, tab2, tab3 = st.tabs(["➕ 記帳與修正", "📊 數據分析", "📋 歷史清單"])

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
                try: default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
                except: default_date = date.today()
            r_date = st.date_input("日期", default_date)
            
        with col2:
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=10.0, value=float(edit_data['amount']) if edit_data else 0.0)
            categories = ['薪水', '獎金', '投資', '洗衣店營收', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '娛樂', '醫療', '軟體訂閱', '其他']
            cat_idx = 0
            if edit_data and edit_data['category'] in categories:
                cat_idx = categories.index(edit_data['category'])
            category = st.selectbox("分類標籤", categories, index=cat_idx)

        note = st.text_input("備註內容", value=edit_data['note'] if edit_data else "")
        submit_btn = st.form_submit_button("🚀 同步到雲端載體")
        
        if submit_btn:
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.rerun()

# --- Tab 2: 統計分析 ---
with tab2:
    if not df.empty:
        total_income = df[df['type'] == '收入']['amount'].sum()
        total_expense = df[df['type'] == '支出']['amount'].sum()
        st.subheader("💰 財務概況")
        c1, c2 = st.columns(2)
        c1.metric("總收入", f"${total_income:,.0f}")
        c2.metric("總支出", f"${total_expense:,.0f}")
        
        fig_pie = px.pie(df[df['type'] == '支出'], values='amount', names='category', title="支出比例")
        st.plotly_chart(fig_pie)
    else:
        st.info("📊 目前尚無數據。")

# --- Tab 3: 歷史清單 ---
with tab3:
    if not df.empty:
        for _, row in df.sort_values(by=['date'], ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"📝 備註: {row['note']}")
                ec1, ec2 = st.columns(2)
                if ec1.button("✏️ 修改", key=f"edit_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if ec2.button("🗑️ 刪除", key=f"del_{row['id']}"):
                    st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                    app.save_data()
                    st.rerun()
