import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import uuid
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 網頁初始設定
# ==========================================
st.set_page_config(page_title="雲端記帳通用版", page_icon="💰", layout="wide")

# ==========================================
# 2. 核心邏輯：雲端載體控制器
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
        if not self.is_connected or not sheet_url: return []
        try:
            df = self.conn.read(spreadsheet=sheet_url, worksheet="Sheet1", ttl=0)
            if df is not None and not df.empty:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                st.session_state.records = df.to_dict('records')
                return st.session_state.records
        except Exception as e:
            st.warning(f"⚠️ 讀取失敗，請檢查網址與權限。")
        return []

    def save_data(self, sheet_url=None):
        if not self.is_connected or not sheet_url: return False
        try:
            df = pd.DataFrame(st.session_state.records) if st.session_state.records else pd.DataFrame(columns=['id', 'date', 'type', 'amount', 'category', 'note'])
            self.conn.update(spreadsheet=sheet_url, worksheet="Sheet1", data=df)
            st.toast("✅ 數據已安全同步！", icon="☁️")
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
# 3. 側邊欄：身份切換
# ==========================================
target_url = None
with st.sidebar:
    st.header("🔐 身份切換")
    try: robot_email = st.secrets["connections"]["gsheets"]["client_email"]
    except: robot_email = "請檢查 Secrets"

    user_type = st.radio("您是誰？", ["我是訪客 (同學)", "我是管理員 (本人)"])
    if user_type == "我是管理員 (本人)":
        pwd = st.text_input("🔑 輸入密碼", type="password")
        if pwd == "5839":
            st.success("管理員已解鎖")
            try: target_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            except: st.error("Secrets 缺少預設網址")
        else: st.warning("請輸入密碼")
    else:
        st.info("👋 歡迎！請使用個人帳本")
        st.code(robot_email, language="text")
        custom_url = st.text_input("🔗 Google Sheets 網址", placeholder="https://docs.google.com/...")
        if custom_url: target_url = custom_url

    if st.button("🔄 讀取帳本"): st.rerun()
    st.divider()
    search_query = st.text_input("搜尋備註...", placeholder="搜尋關鍵字")

# ==========================================
# 4. 數據載入與 UI 呈現
# ==========================================
if not st.session_state.records and target_url:
    app.load_data(target_url)

if not target_url:
    st.title("💰 雲端通用記帳本")
    st.info("👈 請在左側完成設定以開始")
else:
    df = pd.DataFrame(st.session_state.records)
    if not df.empty:
        df['date_obj'] = pd.to_datetime(df['date'])
        if search_query:
            df = df[df['note'].str.contains(search_query, na=False, case=False)]

    st.title("💰 記帳與分析")
    st.caption(f"目前帳本：...{target_url[-15:]}")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["➕ 雲端記帳", "📊 戰力分析", "📋 歷史檔案"])

    # --- Tab 1: 記帳錄入 ---
    with tab1:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
        if edit_item: st.warning(f"🔧 修改中 ID: {st.session_state.editing_id}")
        r_type = st.radio("類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
        with st.form("entry_form", clear_on_submit=(not st.session_state.editing_id)):
            c1, c2 = st.columns(2)
            d_date = date.today()
            if edit_item:
                try: d_date = datetime.strptime(edit_item['date'], '%Y-%m-%d').date()
                except: pass
            with c1: r_date = st.date_input("日期", d_date)
            with c2:
                r_amount = st.number_input("金額", min_value=0.0, step=10.0, value=float(edit_item['amount']) if edit_item else 0.0)
                cats = ['薪水', '獎金', '投資', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
                r_cat = st.selectbox("分類", cats, index=cats.index(edit_item['category']) if edit_item and edit_item['category'] in cats else 0)
            r_note = st.text_input("備註", value=edit_item['note'] if edit_item else "")
            if st.form_submit_button("🚀 同步至雲端", use_container_width=True):
                if r_amount > 0:
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()

    # --- Tab 2: 戰力分析 (新增預算進度條) ---
    with tab2:
        if not df.empty:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
            
            # --- 核心：預算防禦線 ---
            st.subheader("🎯 本月預算防禦線")
            curr_month = datetime.now().strftime('%Y-%m')
            # 篩選當月資料
            month_mask = (df['date_obj'].dt.strftime('%Y-%m') == curr_month)
            month_ex = df[month_mask & (df['type'] == '支出')]['amount'].sum()
            
            c_budget, c_info = st.columns([1, 2])
            with c_budget:
                budget = st.number_input("設定每月預算", min_value=1, value=20000, step=1000)
            
            # 計算比例
            ratio = min(month_ex / budget, 1.0)
            percent = (month_ex / budget) * 100
            
            # 顯示進度條
            st.progress(ratio)
            
            # 根據比例給予提示
            if percent < 70:
                st.success(f"目前已花費 ${month_ex:,.0f} ({percent:.1f}%)，進度安全！")
            elif percent < 90:
