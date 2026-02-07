import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import uuid
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 網頁初始設定
# ==========================================
st.set_page_config(page_title="雲端理財 App", page_icon="💰", layout="wide")

# ==========================================
# 2. 核心邏輯：雲端載體控制器
# ==========================================
class CloudAccounting:
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.is_connected = True
        except Exception as e:
            st.error(f"⚠️ 連線失敗：{e}")
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
        except Exception:
            pass
        return []

    def save_data(self, sheet_url=None):
        if not self.is_connected or not sheet_url: return False
        try:
            df = pd.DataFrame(st.session_state.records) if st.session_state.records else pd.DataFrame(columns=['id', 'date', 'type', 'amount', 'category', 'note'])
            self.conn.update(spreadsheet=sheet_url, worksheet="Sheet1", data=df)
            st.toast("✅ 同步成功！", icon="☁️")
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
# 3. 網址參數偵測 (App 化核心)
# ==========================================
params = st.query_params
sheet_id = params.get("s")
auto_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit" if sheet_id else None

# ==========================================
# 4. 側邊欄：身份與搜尋
# ==========================================
target_url = None
with st.sidebar:
    st.header("🔐 帳本設定")
    
    # 決定 radio 的預設位置 (如果有自動網址，預設選訪客)
    radio_idx = 0 if auto_url else 1
    user_type = st.radio("您的身份：", ["我是訪客", "我是管理員 (本人)"], index=radio_idx)
    
    if user_type == "我是管理員 (本人)":
        pwd = st.text_input("🔑 密碼", type="password")
        if pwd == "5839":
            try: target_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            except: st.error("Secrets 缺少預設網址")
        else: st.warning("請輸入密碼解鎖")
            
    else: # 訪客模式
        if auto_url:
            st.success("✅ 已自動識別帳本連結")
            target_url = auto_url
            if st.button("🗑️ 清除自動登入"):
                st.query_params.clear()
                st.rerun()
        else:
            try: robot_email = st.secrets["connections"]["gsheets"]["client_email"]
            except: robot_email = "請檢查 Secrets"
            st.info("👋 請連接您的試算表")
            st.code(robot_email, language="text")
            st.caption("1. 複製上方 Email 並分享權限")
            custom_url = st.text_input("🔗 2. 貼上您的試算表網址")
            if custom_url: target_url = custom_url

    if st.button("🔄 刷新數據"):
        app.load_data(target_url)
        st.rerun()
        
    st.divider()
    search_query = st.text_input("🔍 搜尋歷史紀錄", placeholder="輸入關鍵字")

# ==========================================
# 5. 主畫面顯示
# ==========================================
if not st.session_state.records and target_url:
    app.load_data(target_url)

if not target_url:
    st.title("💰 雲端理財 App")
    st.info("👈 請在左側完成帳本設定。")
else:
    df = pd.DataFrame(st.session_state.records)
    if not df.empty and search_query:
        df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

    tab1, tab2, tab3 = st.tabs(["➕ 快速記帳", "📊 數據分析", "📋 紀錄明細"])

    with tab1:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
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
            if st.form_submit_button("🚀 同步雲端", use_container_width=True):
                if r_amount > 0:
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()

    with tab2:
        if not df.empty:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
            df['date_obj'] = pd.to_datetime(df['date'])
            st.subheader("🎯 當月消費預算")
            curr_m = datetime.now().strftime('%Y-%m')
            m_ex = df[(df['date_obj'].dt.strftime('%Y-%m') == curr_m) & (df['type'] == '支出')]['amount'].sum()
            budget = st.number_input("每月預算額度", min_value=1, value=20000)
            st.progress(min(m_ex/budget, 1.0))
            st.write(f"已花費: ${m_ex:,.0f} ({ (m_ex/budget)*100 :.1f}%)")
            st.divider()
            t_in, t_ex = df[df['type'] == '收入']['amount'].sum(), df[df['type'] == '支出']['amount'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("總收入", f"${t_in:,.0f}"); m2.metric("總支出", f"${t_ex:,.0f}"); m3.metric("淨資產", f"${t_in - t_ex:,.0f}")
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.bar(df[df['type'] == '收入'].groupby('category')['amount'].sum().reset_index(), x='category', y='amount', title="收入來源", color='category'), use_container_width=True)
            with g2: st.plotly_chart(px.pie(df[df['type'] == '支出'].groupby('category')['amount'].sum().reset_index(), values='amount', names='category', title="支出占比", hole=0.3), use_container_width=True)
        else: st.info("尚無數據")

    with tab3:
        if not df.empty:
            df['m_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
            for m in sorted(df['m_str'].unique(), reverse=True):
                m_df = df[df['m_str'] == m].sort_values(by='date', ascending=False)
                m_in, m_ex = m_df[m_df['type']=='收入']['amount'].sum(), m_df[m_df['type']=='支出']['amount'].sum()
                with st.expander(f"📅 {m} 月數據 (盈餘: ${m_in - m_ex:,.0f})", expanded=(m == datetime.now().strftime('%Y-%m'))):
                    for _, row in m_df.iterrows():
                        c_dt, c_if, c_at, c_op = st.columns([2, 4, 2, 2])
                        c_dt.write(row['date'])
                        c_if.write(f"[{row['category']}] {row['note']}")
                        c_at.markdown(f":{ 'green' if row['type'] == '收入' else 'red' }[${row['amount']:,.0f}]")
                        c1, c2 = c_op.columns(2)
                        if c1.button("✏️", key=f"e_{row['id']}"): st.session_state.editing_id = row['id']; st.rerun()
                        if c2.button("🗑️", key=f"d_{row['id']}"): st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]; app.save_data(target_url); st.rerun()
