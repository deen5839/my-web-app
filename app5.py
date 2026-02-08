import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import uuid
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 網頁初始設定
# ==========================================
st.set_page_config(page_title="雲端理財旗艦版", page_icon="📈", layout="wide")

# 加點 CSS 修正你看到的「數字被擋住」問題
# 修正後的第 14 行
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 32px; font-weight: bold; }
    h1 { color: #1E88E5; padding-bottom: 0px; }
    .report-box { border: 2px solid #f0f2f6; border-radius: 10px; padding: 20px; background-color: #f8f9fb; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True) # 注意這裡改成了 unsafe_allow_html

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
        if 'records' not in st.session_state: st.session_state.records = []
        if 'editing_id' not in st.session_state: st.session_state.editing_id = None

    def load_data(self, sheet_url=None):
        if not self.is_connected or not sheet_url: return []
        try:
            df = self.conn.read(spreadsheet=sheet_url, worksheet="Sheet1", ttl=0)
            if df is not None and not df.empty:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                st.session_state.records = df.to_dict('records')
                return st.session_state.records
        except: pass
        return []

    def save_data(self, sheet_url=None):
        if not self.is_connected or not sheet_url: return False
        try:
            df = pd.DataFrame(st.session_state.records) if st.session_state.records else pd.DataFrame(columns=['id', 'date', 'type', 'amount', 'category', 'note'])
            self.conn.update(spreadsheet=sheet_url, worksheet="Sheet1", data=df)
            st.toast("✅ 數據已同步至雲端！")
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
# 3. 帳號設定 (此處請保持你原本的 ID)
# ==========================================
params = st.query_params
url_id = params.get("s")
auto_url = f"https://docs.google.com/spreadsheets/d/{url_id}/edit" if url_id else None

FRIENDS_DB = {
    "管理員 (本人)": {"id": "1dKLbifoTDOgeUPWasPmcbgl4wLu0_V6hHnCpropVs4k", "pin": "5839"},
    "哥哥": {"id": "請填入ID", "pin": "0000"},
}

target_url = None
with st.sidebar:
    st.header("🔐 系統登入")
    if auto_url:
        target_url = auto_url
        if st.button("🚪 登出系統"): st.query_params.clear(); st.rerun()
    else:
        user_choice = st.selectbox("請選擇身份：", ["---"] + list(FRIENDS_DB.keys()))
        if user_choice in FRIENDS_DB:
            user_pin = st.text_input(f"通行碼", type="password")
            if user_pin == FRIENDS_DB[user_choice]["pin"]:
                target_url = f"https://docs.google.com/spreadsheets/d/{FRIENDS_DB[user_choice]['id']}/edit"
    st.divider()
    if st.button("🔄 刷新雲端資料"): app.load_data(target_url); st.rerun()
    if st.session_state.records:
        csv = pd.DataFrame(st.session_state.records).to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載 CSV 備份", data=csv, file_name=f"finance_{date.today()}.csv")

# ==========================================
# 4. 主介面顯示
# ==========================================
if target_url:
    if not st.session_state.records: app.load_data(target_url)
    df = pd.DataFrame(st.session_state.records)
    
    tab1, tab2, tab3 = st.tabs(["➕ 快速記帳", "📈 趨勢分析", "📋 歷史明細"])

    # --- Tab 2: 趨勢分析 (大標題與下拉選單版) ---
    with tab2:
        if not df.empty:
            df['date_obj'] = pd.to_datetime(df['date'])
            df = df.sort_values('date_obj')
            now = datetime.now()
            
            # --- 【 第一部分：年度結算 】 ---
            st.markdown(f"# 🏆 {now.year} 年度全局結算")
            year_df = df[df['date_obj'].dt.year == now.year]
            y_in = year_df[year_df['type'] == '收入']['amount'].sum()
            y_ex = year_df[year_df['type'] == '支出']['amount'].sum()
            y_net = y_in - y_ex
            
            with st.container():
                st.markdown('<div class="report-box">', unsafe_allow_html=True)
                y1, y2, y3 = st.columns(3)
                y1.metric("年度總收入", f"${y_in:,.0f}")
                y2.metric("年度總支出", f"${y_ex:,.0f}", delta=f"-{y_ex:,.0f}", delta_color="inverse")
                y3.metric("年度總結餘", f"${y_net:,.0f}")
                st.markdown('</div>', unsafe_allow_html=True)

            # --- 【 第二部分：月份下拉選單結算 】 ---
            st.divider()
            st.markdown("# 📊 月份數據查詢")
            
            # 取得所有月份清單
            df['month_key'] = df['date_obj'].dt.strftime('%Y-%m')
            month_list = sorted(df['month_key'].unique(), reverse=True)
            selected_month = st.selectbox("請選擇要查詢的月份：", month_list, index=0)
            
            # 計算選擇月份的資料
            m_df = df[df['month_key'] == selected_month]
            m_in = m_df[m_df['type'] == '收入']['amount'].sum()
            m_ex = m_df[m_df['type'] == '支出']['amount'].sum()
            m_net = m_in - m_ex

            st.markdown(f"### 📅 {selected_month} 財務結算")
            ma, mb, mc = st.columns(3)
            ma.metric("該月總收入", f"${m_in:,.0f}")
            mb.metric("該月總支出", f"${m_ex:,.0f}", delta=f"-{m_ex:,.0f}", delta_color="inverse")
            mc.metric("該月餘額", f"${m_net:,.0f}")

            # --- 圖表 ---
            st.divider()
            st.subheader("📈 資產增長趨勢")
            df['net_val'] = df.apply(lambda x: x['amount'] if x['type'] == '收入' else -x['amount'], axis=1)
            df['cumulative_balance'] = df['net_val'].cumsum()
            st.plotly_chart(px.line(df, x='date_obj', y='cumulative_balance', markers=True, title="資產變化曲線"), use_container_width=True)

    with tab1: # (保持不變)
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
        r_type = st.radio("類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: r_date = st.date_input("日期", date.today())
            with c2:
                r_amount = st.number_input("金額", min_value=0.0, value=float(edit_item['amount']) if edit_item else 0.0)
                cats = ['薪水', '獎金', '投資', '發票', '洗衣店', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
                r_cat = st.selectbox("分類", cats)
            r_note = st.text_input("備註", value=edit_item['note'] if edit_item else "")
            if st.form_submit_button("💾 儲存並同步", use_container_width=True):
                if r_amount > 0:
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()

    with tab3: # (明細)
        if not df.empty:
            for m in sorted(df['month_key'].unique(), reverse=True):
                with st.expander(f"📅 {m} 月份明細"):
                    m_data = df[df['month_key'] == m].sort_values(by='date', ascending=False)
                    for _, row in m_data.iterrows():
                        col1, col2, col3, col4 = st.columns([2, 5, 3, 2])
                        col1.write(f"{row['date'][5:]}")
                        col2.write(f"**{row['category']}** | {row['note']}")
                        color = "green" if row['type'] == "收入" else "red"
                        col3.markdown(f"**:{color}[${row['amount']:,.0f}]**")
                        b1, b2 = col4.columns(2)
                        if b1.button("✏️", key=f"e_{row['id']}"): st.session_state.editing_id = row['id']; st.rerun()
                        if b2.button("🗑️", key=f"d_{row['id']}"): 
                            st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                            app.save_data(target_url); st.rerun()
else:
    st.title("💰 歡迎使用雲端理財系統")
    st.warning("👈 請在左側選單登入")
