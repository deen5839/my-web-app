import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import uuid
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 網頁初始設定
# ==========================================
st.set_page_config(page_title="雲端理財專業 App", page_icon="💰", layout="wide")

# ==========================================
# 2. 核心邏輯控制器 (含安全保險絲)
# ==========================================
class CloudAccounting:
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.is_connected = True
        except Exception as e:
            st.error(f"⚠️ 連線初始化失敗：{e}")
            self.is_connected = False
        if 'records' not in st.session_state: st.session_state.records = []
        if 'editing_id' not in st.session_state: st.session_state.editing_id = None

    def load_data(self, sheet_url=None):
        if not self.is_connected or not sheet_url: 
            return []
        try:
            df = self.conn.read(spreadsheet=sheet_url, worksheet="Sheet1", ttl=0)
            if df is not None and not df.empty:
                # 檢查必要欄位拼字
                required_cols = ['id', 'date', 'type', 'amount', 'category', 'note']
                missing = [c for c in required_cols if c not in df.columns]
                if missing:
                    st.error(f"🚨 試算表缺少欄位：{', '.join(missing)}")
                    return []
                
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                st.session_state.records = df.to_dict('records')
                return st.session_state.records
            else:
                st.info("💡 目前帳本是空的，開始記第一筆帳吧！")
        except Exception as e:
            st.error(f"🚨 讀取發生錯誤：{e}")
        return []

    def save_data(self, sheet_url=None):
        if not self.is_connected or not sheet_url: return False
        
        # 🛡️ 安全保險絲：防止空數據覆蓋雲端
        if not st.session_state.records:
            st.warning("⚠️ App 內尚無數據，已攔截存檔請求以保護雲端資料。")
            return False
            
        try:
            df = pd.DataFrame(st.session_state.records)
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
# 3. 網址參數偵測 (優先級最高)
# ==========================================
params = st.query_params
url_id = params.get("s")
auto_url = f"https://docs.google.com/spreadsheets/d/{url_id}/edit" if url_id else None

# ==========================================
# 4. 朋友資料庫 (請在此處更新同學 ID)
# ==========================================
FRIENDS_DB = {
    "管理員 (本人)": {"id": "1dKLbifoTDOgeUPWasPmcbgl4wLu0_V6hHnCpropVs4k", "pin": "5839"},
    "哥哥": {"id": "請填入哥哥的ID", "pin": "0000"},
    "同學 A": {"id": "請填入同學的ID", "pin": "1234"},
}

# ==========================================
# 5. 側邊欄：登入與搜尋
# ==========================================
target_url = None
with st.sidebar:
    st.header("🔐 系統登入")
    
    if auto_url:
        st.success("✅ 專屬連結偵測成功")
        target_url = auto_url
        if st.button("🚪 登出"):
            st.query_params.clear()
            st.rerun()
    else:
        user_choice = st.selectbox("請選擇身份：", ["---"] + list(FRIENDS_DB.keys()) + ["手動輸入網址 (訪客)"])
        
        if user_choice in FRIENDS_DB:
            user_pin = st.text_input(f"輸入 {user_choice} 的通行碼", type="password")
            if user_pin == FRIENDS_DB[user_choice]["pin"]:
                st.success("🔓 認證成功")
                target_url = f"https://docs.google.com/spreadsheets/d/{FRIENDS_DB[user_choice]['id']}/edit"
            elif user_pin:
                st.error("❌ 通行碼錯誤")
        
        elif user_choice == "手動輸入網址 (訪客)":
            custom_url = st.text_input("🔗 請貼上您的試算表網址")
            if custom_url: target_url = custom_url

    if st.button("🔄 刷新/載入帳本"):
        st.session_state.records = []
        st.rerun()
    
    st.divider()
    search_query = st.text_input("🔍 搜尋歷史紀錄", placeholder="搜尋分類、金額或備註")

# ==========================================
# 6. 主介面顯示
# ==========================================
if target_url:
    if not st.session_state.records:
        app.load_data(target_url)
    
    df = pd.DataFrame(st.session_state.records)
    if not df.empty and search_query:
        # 全域關鍵字搜尋
        df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

    st.title("💰 我的雲端理財帳本")
    tab1, tab2, tab3 = st.tabs(["➕ 快速記帳", "📊 數據分析", "📋 歷史明細"])

    # --- Tab 1: 記帳 ---
    with tab1:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
        r_type = st.radio("收支類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: r_date = st.date_input("日期", date.today())
            with c2:
                r_amount = st.number_input("金額", min_value=0.0, step=10.0, value=float(edit_item['amount']) if edit_item else 0.0)
                cats = ['薪水', '獎金', '投資', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
                r_cat = st.selectbox("項目分類", cats)
            r_note = st.text_input("詳細備註", value=edit_item['note'] if edit_item else "")
            if st.form_submit_button("🚀 同步至雲端", use_container_width=True):
                if r_amount > 0:
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()

    # --- Tab 2: 分析 (新增三大指標) ---
    with tab2:
        if not df.empty:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
            
            # --- 核心數據指標 ---
            st.subheader("💰 財務總覽")
            total_in = df[df['type'] == '收入']['amount'].sum()
            total_ex = df[df['type'] == '支出']['amount'].sum()
            net_income = total_in - total_ex
            
            m1, m2, m3 = st.columns(3)
            m1.metric("累積總收入", f"${total_in:,.0f}")
            m2.metric("累積總支出", f"${total_ex:,.0f}", delta=f"-{total_ex:,.0f}", delta_color="inverse")
            m3.metric("目前淨收入 (餘額)", f"${net_income:,.0f}", delta=f"{ (net_income/total_in*100 if total_in > 0 else 0):.1f}% 儲蓄率")
            
            st.divider()

            # --- 當月消費進度 ---
            st.subheader("🎯 當月消費進度")
            curr_month = datetime.now().strftime('%Y-%m')
            month_ex = df[(pd.to_datetime(df['date']).dt.strftime('%Y-%m') == curr_month) & (df['type'] == '支出')]['amount'].sum()
            budget = st.number_input("設定每月預算", min_value=1, value=20000)
            st.progress(min(month_ex/budget, 1.0))
            st.write(f"本月累計支出: **${month_ex:,.0f}** / ${budget:,.0f}")
            
            st.divider()
            
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.bar(df[df['type'] == '收入'].groupby('category')['amount'].sum().reset_index(), x='category', y='amount', title="收入來源", color='category'), use_container_width=True)
            with g2: st.plotly_chart(px.pie(df[df['type'] == '支出'].groupby('category')['amount'].sum().reset_index(), values='amount', names='category', title="支出占比", hole=0.3), use_container_width=True)
        else: st.info("尚無數據紀錄。")

    # --- Tab 3: 明細 ---
    with tab3:
        if not df.empty:
            months = sorted(pd.to_datetime(df['date']).dt.strftime('%Y-%m').unique(), reverse=True)
            for m in months:
                with st.expander(f"📅 {m} 月份紀錄"):
                    m_df = df[pd.to_datetime(df['date']).dt.strftime('%Y-%m') == m].sort_values(by='date', ascending=False)
                    st.dataframe(m_df[['date', 'type', 'category', 'amount', 'note']], use_container_width=True)
        else: st.info("尚無歷史明細。")

else:
    st.title("💰 歡迎使用雲端理財系統")
    st.warning("👈 請在左側選單選擇身份並輸入「通行碼」以載入帳本。")
