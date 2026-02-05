import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io
import uuid
import json
import os
from streamlit_gsheets import GSheetsConnection

# 1. 網頁初始設定
st.set_page_config(page_title="個人理財數據帳本", page_icon="💰", layout="wide")

# 2. 數據處理核心
class WebAccounting:
    def __init__(self):
        self.sheet_url = "https://docs.google.com/spreadsheets/d/1wc7rLawk5i6gfMEFw8p9hK_gUFlUIvCuL6-FPETNsw8/edit"
        try:
            # 💡 這裡會嘗試讀取 secrets，如果沒設好會噴錯，但我們不怕
            self.conn = st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            st.error(f"⚠️ 雲端連線尚未設定憑證：{e}")

        # 初始化 session_state
        if 'records' not in st.session_state:
            st.session_state.records = self.load_data()
        if 'editing_id' not in st.session_state:
            st.session_state.editing_id = None

    def load_data(self):
        try:
            # 優先嘗試從雲端讀取
            df = self.conn.read(spreadsheet=self.sheet_url, worksheet="Sheet1", ttl=0)
            if df is not None and not df.empty:
                return df.to_dict('records')
        except:
            pass
        return []

    def save_data(self):
        try:
            df = pd.DataFrame(st.session_state.records)
            # 嘗試存入雲端
            st.cache_data.clear()
            self.conn.update(spreadsheet=self.sheet_url, worksheet="Sheet1", data=df)
            st.toast("✅ 雲端存檔成功！", icon="☁️")
        except:
            # 如果雲端失敗，這裡會提醒你下載備份，數據才不會白費
            st.sidebar.error("🚨 雲端存檔失敗！請務必下載 Excel 備份。")
        return True

    def add_or_update_record(self, r_date, r_type, amount, category, note):
        if st.session_state.editing_id:
            for r in st.session_state.records:
                if r['id'] == st.session_state.editing_id:
                    r.update({'date': r_date.strftime('%Y-%m-%d'), 'type': r_type, 'amount': amount, 'category': category, 'note': note})
            st.session_state.editing_id = None
        else:
            new_id = str(uuid.uuid4())[:8]
            st.session_state.records.append({'id': new_id, 'date': r_date.strftime('%Y-%m-%d'), 'type': r_type, 'amount': amount, 'category': category, 'note': note})
        self.save_data()

# 初始化 App
if 'app' not in st.session_state:
    st.session_state.app = WebAccounting()
app = st.session_state.app

# --- UI 介面開始 ---
st.title("💰 個人理財：數據記錄帳本")

# 側邊欄導出功能
with st.sidebar:
    st.header("📊 檔案導出")
    if st.session_state.records:
        export_df = pd.DataFrame(st.session_state.records)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False)
        st.download_button(label="📥 下載 Excel 備份檔", data=buffer.getvalue(), file_name=f"理財記錄_{date.today()}.xlsx")

# 招呼語與分頁
taiwan_now = datetime.now() + timedelta(hours=8)
st.info(f"🌙 晚上好！辛苦了。系統時間：{taiwan_now.strftime('%H:%M')}")

tab1, tab2, tab3 = st.tabs(["➕ 記帳", "📊 分析", "📋 歷史"])

with tab1:
    with st.form("input_form"):
        r_date = st.date_input("日期", date.today())
        r_type = st.radio("類型", ["支出", "收入"], horizontal=True)
        amount = st.number_input("金額", min_value=0.0)
        category = st.selectbox("分類", ["飲食", "交通", "購物", "薪水", "其他"])
        note = st.text_input("備註")
        if st.form_submit_button("🚀 同步雲端"):
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.rerun()

with tab3:
    if st.session_state.records:
        for r in st.session_state.records:
            with st.expander(f"{r['date']} - {r['type']} - ${r['amount']}"):
                st.write(f"備註: {r['note']}")
                if st.button("🗑️ 刪除", key=r['id']):
                    st.session_state.records = [rec for rec in st.session_state.records if rec['id'] != r['id']]
                    app.save_data()
                    st.rerun()
    else:
        st.write("目前沒有紀錄")
