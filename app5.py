import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import uuid
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 網頁初始設定
# ==========================================
st.set_page_config(page_title="理財 App 專業安全版", page_icon="🔐", layout="wide")

# ==========================================
# 2. 核心邏輯控制器
# ==========================================
class CloudAccounting:
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.is_connected = True
        except Exception as e:
            st.error(f"⚠️ 連線初始化失敗：{e}")
            self.is_connected = False

        if 'records' not in st.session_state:
            st.session_state.records = []
        if 'editing_id' not in st.session_state:
            st.session_state.editing_id = None

    def load_data(self, sheet_url=None):
        if not self.is_connected or not sheet_url: 
            return []
        try:
            # 讀取試算表資料
            df = self.conn.read(spreadsheet=sheet_url, worksheet="Sheet1", ttl=0)
            if df is not None and not df.empty:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                st.session_state.records = df.to_dict('records')
                return st.session_state.records
        except Exception as e:
            # 💡 這行會顯示真正的讀取錯誤，幫助診斷為什麼沒數據
            st.error(f"🚨 讀取發生錯誤：{e}")
        return []

    def save_data(self, sheet_url=None):
        if not self.is_connected or not sheet_url: 
            return False
        try:
            df = pd.DataFrame(st.session_state.records) if st.session_state.records else pd.DataFrame(columns=['id', 'date', 'type', 'amount', 'category', 'note'])
            self.conn.update(spreadsheet=sheet_url, worksheet="Sheet1", data=df)
            st.toast("✅ 數據已成功同步！", icon="☁️")
            return True
        except Exception as e:
            st.error(f"❌ 寫入失敗：{e}")
            return False

    def add_or_update(self, r_date, r_type, amount, category, note, sheet_url=None):
        if st.session_state.editing_id:
            for r in st.session_state.records:
                if r['id'] == st.session_state.editing_id:
                    r.update({'date': r_date.strftime('%Y-%m-%d'), 'type': r_type, 'amount': amount, 'category': category, 'note': note})
                    break
            st.session_state.editing_id = None
        else:
            st.session_state.records.append({'id': str(uuid.uuid4())[:8], 'date': r_date.strftime('%Y-%m-%d'), 'type': r_type, 'amount': amount, 'category': category, 'note': note})
        self.save_data(sheet_url)

if 'app' not in st.session_state: st.session_state.app = CloudAccounting()
app = st.session_state.app

# ==========================================
# 3. 網址參數偵測 (解決 NameError 的關鍵)
# ==========================================
# 必須在 sidebar 使用前先定義好 auto_url
params = st.query_params
url_id = params.get("s")
auto_url = f"https://docs.google.com/spreadsheets/d/{url_id}/edit" if url_id else None

# ==========================================
# 4. 朋友資料庫
# ==========================================
FRIENDS_DB = {
    "管理員 (本人)": {"id": "1dKLbifoTDOgeUPWasPmcbgl4wLu0_V6hHnCpropVs4k", "pin": "5839"},
    "同學 A (小明)": {"id": "這裡換成小明的ID", "pin": "1234"},
    "同學 B (小美)": {"id": "這裡換成小美的ID", "pin": "8888"},
}

# ==========================================
# 5. 側邊欄：登入檢查
# ==========================================
target_url = None
with st.sidebar:
    st.header("🔐 系統登入")
    
    if auto_url:
        st.success("✅ 專屬連結已偵測")
        target_url = auto_url
        if st.button("門 登出專屬帳本"):
            st.query_params.clear()
            st.rerun()
    else:
        # 根據是否有 auto_url 決定 radio 的預設位置
        user_choice = st.selectbox("請選擇您的身份：", ["---"] + list(FRIENDS_DB.keys()) + ["手動輸入網址 (訪客)"])
        
        if user_choice in FRIENDS_DB:
            user_pin = st.text_input(f"請輸入 {user_choice} 的通關密碼", type="password")
            if user_pin == FRIENDS_DB[user_choice]["pin"]:
                st.success("🔓 認證成功")
                target_url = f"https://docs.google.com/spreadsheets/d/{FRIENDS_DB[user_choice]['id']}/edit"
            elif user_pin:
                st.error("❌ 密碼錯誤")
        
        elif user_choice == "手動輸入網址 (訪客)":
            custom_url = st.text_input("🔗 請貼上您的試算表網址")
            if custom_url: target_url = custom_url

    if st.button("🔄 刷新帳本"):
        st.session_state.records = []
        st.rerun()
    
    st.divider()
    search_query = st.text_input("🔍 全局搜尋", placeholder="搜尋關鍵字...")

# ==========================================
# 6. 主介面顯示
# ==========================================
if target_url:
    if not st.session_state.records: 
        app.load_data(target_url)
    
    df = pd.DataFrame(st.session_state.records)
    if not df.empty and search_query:
        df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

    st.title("💰 我的理財雲端帳本")
    tab1, tab2, tab3 = st.tabs(["➕ 記帳", "📊 分析", "📋 明細"])

    with tab1:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
        r_type = st.radio("類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: r_date = st.date_input("日期", date.today())
            with c2:
                r_amount = st.number_input("金額", min_value=0.0, value=float(edit_item['amount']) if edit_item else 0.0)
                cats = ['薪水', '獎金', '投資', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
                r_cat = st.selectbox("分類", cats)
            r_note = st.text_input("備註", value=edit_item['note'] if edit_item else "")
            if st.form_submit_button("🚀 存入雲端"):
                if r_amount > 0:
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()

    with tab2:
        if not df.empty:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            curr_ex = df[(pd.to_datetime(df['date']).dt.strftime('%Y-%m') == datetime.now().strftime('%Y-%m')) & (df['type'] == '支出')]['amount'].sum()
            st.subheader("🎯 當月消費進度")
            st.progress(min(curr_ex/20000, 1.0))
            st.write(f"本月已花費: ${curr_ex:,.0f}")
            st.plotly_chart(px.pie(df[df['type'] == '支出'], values='amount', names='category', hole=0.3), use_container_width=True)
        else: st.info("尚無數據")

    with tab3:
        if not df.empty:
            for m in sorted(pd.to_datetime(df['date']).dt.strftime('%Y-%m').unique(), reverse=True):
                with st.expander(f"📅 {m}"):
                    month_df = df[pd.to_datetime(df['date']).dt.strftime('%Y-%m') == m]
                    st.table(month_df[['date', 'category', 'amount', 'note']])
        else: st.info("尚無紀錄")
else:
    st.title("💰 歡迎使用雲端理財系統")
    st.warning("👈 請在左側選單選擇身份並輸入「通關密碼」以載入帳本。")
