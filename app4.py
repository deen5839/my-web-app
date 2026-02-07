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
            st.warning(f"⚠️ 無法讀取資料，請確認：\n1. 網址是否正確？\n2. 是否已共用給機器人？\n錯誤訊息：{e}")
        return []

    def save_data(self, sheet_url=None):
        if not self.is_connected or not sheet_url: return False
        try:
            df = pd.DataFrame(st.session_state.records) if st.session_state.records else pd.DataFrame(columns=['id', 'date', 'type', 'amount', 'category', 'note'])
            self.conn.update(spreadsheet=sheet_url, worksheet="Sheet1", data=df)
            st.toast("✅ 數據已安全同步至雲端！", icon="☁️")
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
# 3. 側邊欄：多人共用與隱私設定 (核心修改區)
# ==========================================
target_url = None

with st.sidebar:
    st.header("🔐 身份切換")
    
    # --- A. 取得機器人 Email (給同學複製用) ---
    try:
        robot_email = st.secrets["connections"]["gsheets"]["client_email"]
    except:
        robot_email = "(請檢查 Secrets 設定)"

    # --- B. 登入系統 ---
    user_type = st.radio("您是誰？", ["我是訪客 (同學)", "我是管理員 (本人)"])
    
    if user_type == "我是管理員 (本人)":
        pwd = st.text_input("🔑 輸入密碼", type="password")
        # ⚠️ 這裡設定你的簡易密碼，例如 "5839"
        if pwd == "5839":
            st.success("歡迎回來！已載入您的私人帳本")
            try:
                target_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            except:
                st.error("Secrets 裡找不到預設網址")
        else:
            st.warning("請輸入正確密碼以解鎖資料")
            
    else: # 訪客模式
        st.info("👋 歡迎！請使用自己的 Google Sheet")
        st.markdown("### 第 1 步：複製機器人 Email")
        st.code(robot_email, language="text")
        st.caption("請將您的試算表「共用」給這個 Email (權限選編輯者)")
        
        st.markdown("### 第 2 步：貼上您的網址")
        custom_url = st.text_input("🔗 Google Sheets 網址", placeholder="https://docs.google.com/...")
        if custom_url:
            target_url = custom_url

    if st.button("🔄 讀取帳本"):
        st.rerun()
    st.divider()
    search_query = st.text_input("搜尋備註...", placeholder="例如：午餐")

# ==========================================
# 4. 數據載入與 UI
# ==========================================
# 只有當 target_url 有值時才載入資料 (保護隱私)
if not st.session_state.records and target_url:
    app.load_data(target_url)

# 如果沒有網址，顯示歡迎畫面，不要顯示資料
if not target_url:
    st.title("💰 雲端共用記帳本")
    st.info("👈 請在左側選擇身份並設定帳本")
    st.markdown("""
    ### 如何開始？
    1. **建立一個新的 Google Sheet** (將工作表命名為 `Sheet1`)。
    2. **共用給機器人** (複製左側的 Email)。
    3. **貼上網址** 即可開始記帳！
    """)
else:
    # 這裡開始才是原本的介面
    df = pd.DataFrame(st.session_state.records)
    if not df.empty and search_query:
        df = df[df['note'].str.contains(search_query, na=False, case=False)]

    st.title("💰 記帳本")
    st.caption(f"使用中帳本：...{target_url[-10:] if target_url else ''}")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["➕ 雲端記帳", "📊 戰力分析", "📋 歷史檔案"])

    with tab1:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
        if edit_item: st.warning(f"🔧 修改中 ID: {st.session_state.editing_id}")
        r_type = st.radio("類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
        with st.form("entry_form", clear_on_submit=(not st.session_state.editing_id)):
            c1, c2 = st.columns(2)
            default_date = date.today()
            if edit_item:
                try: default_date = datetime.strptime(edit_item['date'], '%Y-%m-%d').date()
                except: pass
            with c1: r_date = st.date_input("日期", default_date)
            with c2:
                r_amount = st.number_input("金額", min_value=0.0, step=10.0, value=float(edit_item['amount']) if edit_item else 0.0)
                cats = ['薪水', '獎金', '投資', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
                r_cat = st.selectbox("分類", cats, index=cats.index(edit_item['category']) if edit_item and edit_item['category'] in cats else 0)
            r_note = st.text_input("備註", value=edit_item['note'] if edit_item else "")
            if st.form_submit_button("🚀 同步至 Google Sheets", use_container_width=True):
                if r_amount > 0:
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()

    with tab2:
        if not df.empty:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
            total_in = df[df['type'] == '收入']['amount'].sum()
            total_ex = df[df['type'] == '支出']['amount'].sum()
            st.subheader("💰 財務戰力指標")
            m1, m2, m3 = st.columns(3)
            m1.metric("總收入", f"${total_in:,.0f}")
            m2.metric("總支出", f"${total_ex:,.0f}", delta=f"-{total_ex:,.0f}", delta_color="inverse")
            m3.metric("淨資產", f"${total_in - total_ex:,.0f}")
            st.divider()
            g1, g2 = st.columns(2)
            with g1:
                if not df[df['type'] == '收入'].empty: st.plotly_chart(px.bar(df[df['type'] == '收入'].groupby('category')['amount'].sum().reset_index(), x='category', y='amount', title="收入來源", color='category'), use_container_width=True)
            with g2:
                if not df[df['type'] == '支出'].empty: st.plotly_chart(px.pie(df[df['type'] == '支出'].groupby('category')['amount'].sum().reset_index(), values='amount', names='category', title="支出占比", hole=0.3), use_container_width=True)
        else: st.info("☁️ 尚無資料，請先新增記帳")

    with tab3:
        if not df.empty:
            df['date_obj'] = pd.to_datetime(df['date'])
            df['month_str'] = df['date_obj'].dt.strftime('%Y-%m')
            unique_months = sorted(df['month_str'].unique(), reverse=True)
            for m in unique_months:
                month_df = df[df['month_str'] == m].sort_values(by='date', ascending=False)
                m_in = month_df[month_df['type']=='收入']['amount'].sum()
                m_ex = month_df[month_df['type']=='支出']['amount'].sum()
                with st.expander(f"📅 {m} 月結算 (餘額: ${m_in - m_ex:,.0f})", expanded=True):
                    st.caption(f"收入: ${m_in:,.0f} | 支出: ${m_ex:,.0f}")
                    for _, row in month_df.iterrows():
                        col_date, col_info, col_amt, col_act = st.columns([2, 4, 2, 2])
                        with col_date: st.write(row['date'])
                        with col_info: st.write(f"{row['category']} - {row['note']}")
                        with col_amt: 
                            color = "green" if row['type'] == "收入" else "red"
                            st.markdown(f":{color}[${row['amount']:,.0f}]")
                        with col_act:
                            c1, c2 = st.columns(2)
                            if c1.button("✏️", key=f"e_{row['id']}"): st.session_state.editing_id = row['id']; st.rerun()
                            if c2.button("🗑️", key=f"d_{row['id']}"): st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]; app.save_data(target_url); st.rerun()
        else: st.info("☁️ 尚無歷史資料")
