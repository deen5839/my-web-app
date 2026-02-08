import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import uuid
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 網頁初始設定
# ==========================================
st.set_page_config(page_title="雲端理財旗艦版", page_icon="💰", layout="wide")

# CSS：維持大標題與無邊框樣式
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px !important; font-weight: bold; }
    h1 { color: #1E88E5; padding-top: 10px; margin-bottom: 0px; }
    h2 { color: #424242; margin-top: 20px; }
    .report-box { border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; background-color: #fcfcfc; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 核心邏輯控制器
# ==========================================
class CloudAccounting:
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.is_connected = True
        except Exception as e:
            st.error(f"⚠️ 連線失敗：{e}")
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
            st.toast("✅ 雲端同步成功！")
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
# 3. 登入與側邊欄 (搜尋功能加回在此)
# ==========================================
params = st.query_params
url_id = params.get("s")
auto_url = f"https://docs.google.com/spreadsheets/d/{url_id}/edit" if url_id else None

FRIENDS_DB = {
    "管理員 (本人)": {"id": "1dKLbifoTDOgeUPWasPmcbgl4wLu0_V6hHnCpropVs4k", "pin": "5839"},
    "哥哥": {"id": "1vK_O9_f68fX89_p_pS_B6X7X...", "pin": "0000"},
}

target_url = None
with st.sidebar:
    st.header("🔐 系統登入")
    if auto_url:
        target_url = auto_url
        if st.button("🚪 登出系統"): st.query_params.clear(); st.rerun()
    else:
        user_choice = st.selectbox("身份：", ["---"] + list(FRIENDS_DB.keys()))
        if user_choice in FRIENDS_DB:
            user_pin = st.text_input("通行碼", type="password")
            if user_pin == FRIENDS_DB[user_choice]["pin"]:
                target_url = f"https://docs.google.com/spreadsheets/d/{FRIENDS_DB[user_choice]['id']}/edit"
    
    st.divider()
    if st.button("🔄 刷新雲端資料"): app.load_data(target_url); st.rerun()
    
    # --- 搜尋功能回歸 ---
    search_query = st.text_input("🔍 搜尋歷史紀錄", placeholder="搜尋分類、金額或備註")
    
    if st.session_state.records:
        csv = pd.DataFrame(st.session_state.records).to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載 CSV 備份", data=csv, file_name=f"finance_{date.today()}.csv")

# ==========================================
# 4. 主介面顯示 (含搜尋過濾邏輯)
# ==========================================
if target_url:
    if not st.session_state.records: app.load_data(target_url)
    df = pd.DataFrame(st.session_state.records)
    
    # --- 關鍵字過濾邏輯 ---
    if not df.empty and search_query:
        df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
    st.title("💰 雲端記帳本")
    
    st.divider()
    tab1, tab2, tab3 = st.tabs(["➕ 快速記帳", "📈 數據分析", "📋 歷史明細"])

    # --- Tab 2: 數據分析 (維持 3.1 旗艦版配置) ---
    with tab2:
        if not df.empty:
            df['date_obj'] = pd.to_datetime(df['date'])
            df = df.sort_values('date_obj')
            now = datetime.now()
            
            st.markdown(f"# 🏆 {now.year} 年度全局報告")
            year_df = df[df['date_obj'].dt.year == now.year]
            y_in = year_df[year_df['type'] == '收入']['amount'].sum()
            y_ex = year_df[year_df['type'] == '支出']['amount'].sum()
            
            st.markdown('<div class="report-box">', unsafe_allow_html=True)
            y1, y2, y3 = st.columns(3)
            y1.metric("年度總收入", f"${y_in:,.0f}")
            y2.metric("年度總支出", f"${y_ex:,.0f}", delta=f"-{y_ex:,.0f}", delta_color="inverse")
            y3.metric("年度總結餘", f"${y_in - y_ex:,.0f}")
            st.markdown('</div>', unsafe_allow_html=True)

            st.subheader("🎯 當月預算執行進度")
            curr_month_str = now.strftime('%Y-%m')
            this_month_ex = df[(df['date_obj'].dt.strftime('%Y-%m') == curr_month_str) & (df['type'] == '支出')]['amount'].sum()
            budget = st.number_input("設定每月預算上限：", min_value=1000, value=20000, step=1000)
            progress = min(this_month_ex / budget, 1.0)
            st.progress(progress)
            st.write(f"本月已花費: **${this_month_ex:,.0f}** / 預算: **${budget:,.0f}** ({progress*100:.1f}%)")

            st.divider()
            st.markdown("## 📊 月份細節查詢")
            df['month_key'] = df['date_obj'].dt.strftime('%Y-%m')
            month_list = sorted(df['month_key'].unique(), reverse=True)
            selected_month = st.selectbox("切換查看月份：", month_list, index=0)
            
            m_df = df[df['month_key'] == selected_month]
            m_in = m_df[m_df['type'] == '收入']['amount'].sum()
            m_ex = m_df[m_df['type'] == '支出']['amount'].sum()

            m1, m2, m3 = st.columns(3)
            m1.metric("該月收入", f"${m_in:,.0f}")
            m2.metric("該月支出", f"${m_ex:,.0f}")
            m3.metric("該月餘額", f"${m_in - m_ex:,.0f}")

            st.divider()
            g1, g2 = st.columns(2)
            with g1:
                m_exp_df = m_df[m_df['type'] == '支出']
                if not m_exp_df.empty:
                    st.plotly_chart(px.pie(m_exp_df.groupby('category')['amount'].sum().reset_index(), 
                                           values='amount', names='category', title=f"{selected_month} 支出分布", hole=0.4), use_container_width=True)
                else: st.info("該月尚無支出紀錄")
            with g2:
                month_group = df.groupby(['month_key', 'type'])['amount'].sum().reset_index()
                st.plotly_chart(px.bar(month_group, x='month_key', y='amount', color='type', barmode='group', 
                                       title="歷史收支趨勢對比", color_discrete_map={'收入':'#2ca02c', '支出':'#d62728'}), use_container_width=True)
            
            st.subheader("📈 資產成長曲線 (累計結餘)")
            df['net_val'] = df.apply(lambda x: x['amount'] if x['type'] == '收入' else -x['amount'], axis=1)
            df['cumulative'] = df['net_val'].cumsum()
            st.plotly_chart(px.line(df, x='date_obj', y='cumulative', markers=True, title="總資產變化歷程"), use_container_width=True)

    # --- Tab 1: 記帳 & Tab 3: 明細 (保持穩定) ---
    with tab1:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
        r_type = st.radio("收支類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: r_date = st.date_input("日期", date.today())
            with c2:
                r_amount = st.number_input("金額", min_value=0.0, value=float(edit_item['amount']) if edit_item else 0.0)
                cats = ['薪水', '獎金', '投資', '發票', '洗衣店', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
                r_cat = st.selectbox("分類", cats)
            r_note = st.text_input("詳細備註", value=edit_item['note'] if edit_item else "")
            if st.form_submit_button("🚀 同步至雲端", use_container_width=True):
                if r_amount > 0:
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()

    with tab3:
        if not df.empty:
            for m in sorted(df['month_key'].unique(), reverse=True):
                with st.expander(f"📅 {m} 月份詳細清單"):
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
        else: st.info("尚無資料，或搜尋無匹配結果。")
else:
    st.title("💰 歡迎使用雲端理財系統")
    st.warning("👈 請在左側選單登入")
