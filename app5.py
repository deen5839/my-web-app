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
            st.toast("✅ 數據已同步至雲端！", icon="☁️")
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
# 3. 登入設定
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
        if st.button("🚪 登出系統"):
            st.query_params.clear(); st.rerun()
    else:
        user_choice = st.selectbox("請選擇身份：", ["---"] + list(FRIENDS_DB.keys()))
        if user_choice in FRIENDS_DB:
            user_pin = st.text_input(f"通行碼", type="password")
            if user_pin == FRIENDS_DB[user_choice]["pin"]:
                target_url = f"https://docs.google.com/spreadsheets/d/{FRIENDS_DB[user_choice]['id']}/edit"
    
    st.divider()
    if st.button("🔄 刷新雲端資料"):
        app.load_data(target_url); st.rerun()
    
    if st.session_state.records:
        csv = pd.DataFrame(st.session_state.records).to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載備份 (CSV)", data=csv, file_name=f"finance_backup_{date.today()}.csv", mime="text/csv")

# ==========================================
# 4. 主介面顯示
# ==========================================
if target_url:
    if not st.session_state.records: app.load_data(target_url)
    df = pd.DataFrame(st.session_state.records)
    
    tab1, tab2, tab3 = st.tabs(["➕ 快速記帳", "📈 趨勢分析", "📋 歷史明細"])

    with tab1:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
        if edit_item:
            st.warning(f"🔧 修改模式 (ID: {st.session_state.editing_id})")
            if st.button("放棄修改"): st.session_state.editing_id = None; st.rerun()

        r_type = st.radio("收支類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: r_date = st.date_input("日期", date.today())
            with c2:
                r_amount = st.number_input("金額", min_value=0.0, step=10.0, value=float(edit_item['amount']) if edit_item else 0.0)
                cats = ['薪水', '獎金', '投資', '發票', '洗衣店', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
                r_cat = st.selectbox("分類", cats, index=cats.index(edit_item['category']) if edit_item and edit_item['category'] in cats else 0)
            r_note = st.text_input("備註", value=edit_item['note'] if edit_item else "")
            if st.form_submit_button("💾 儲存並同步", use_container_width=True):
                if r_amount > 0:
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()

    # --- Tab 2: 趨勢分析 (強化結算功能) ---
    with tab2:
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            now = datetime.now()
            
            # --- A. 月與年度結算指標 ---
            st.subheader("🏁 財務結算報告")
            
            # 計算本月資料
            curr_month_str = now.strftime('%Y-%m')
            month_df = df[df['date'].dt.strftime('%Y-%m') == curr_month_str]
            m_in = month_df[month_df['type'] == '收入']['amount'].sum()
            m_ex = month_df[month_df['type'] == '支出']['amount'].sum()
            m_net = m_in - m_ex
            
            # 計算年度資料
            curr_year = now.year
            year_df = df[df['date'].dt.year == curr_year]
            y_in = year_df[year_df['type'] == '收入']['amount'].sum()
            y_ex = year_df[year_df['type'] == '支出']['amount'].sum()
            y_net = y_in - y_ex

            # 顯示指標
            col_a, col_b = st.columns(2)
            with col_a:
                st.info(f"📅 {now.strftime('%m')} 月份結算")
                ma, mb, mc = st.columns(3)
                ma.metric("本月收入", f"${m_in:,.0f}")
                mb.metric("本月支出", f"${m_ex:,.0f}", delta=f"-{m_ex:,.0f}", delta_color="inverse")
                mc.metric("本月餘額", f"${m_net:,.0f}", delta=f"{'盈餘' if m_net>=0 else '透支'}")
                
            with col_b:
                st.success(f"🎊 {curr_year} 年度結算")
                ya, yb, yc = st.columns(3)
                ya.metric("年度總收入", f"${y_in:,.0f}")
                yb.metric("年度總支出", f"${y_ex:,.0f}", delta=f"-{y_ex:,.0f}", delta_color="inverse")
                yc.metric("年度總純利", f"${y_net:,.0f}", delta=f"儲蓄率 {(y_net/y_in*100 if y_in>0 else 0):.1f}%")

            # --- B. 資產成長趨勢 ---
            st.divider()
            st.subheader("📈 資產增長趨勢")
            df['net_val'] = df.apply(lambda x: x['amount'] if x['type'] == '收入' else -x['amount'], axis=1)
            df['cumulative_balance'] = df['net_val'].cumsum()
            st.plotly_chart(px.line(df, x='date', y='cumulative_balance', title="總資產變化曲線 (累計餘額)", markers=True, color_discrete_sequence=['#00CC96']), use_container_width=True)
            
            # --- C. 消費分布分析 ---
            st.divider()
            g1, g2 = st.columns(2)
            with g1:
                # 支出占比圓餅圖
                exp_df = df[df['type'] == '支出']
                if not exp_df.empty:
                    st.plotly_chart(px.pie(exp_df.groupby('category')['amount'].sum().reset_index(), values='amount', names='category', title="全期間支出類別分布", hole=0.4), use_container_width=True)
                else: st.write("尚無支出數據")
            with g2:
                # 每月收支對比柱狀圖
                df['month'] = df['date'].dt.strftime('%Y-%m')
                month_group = df.groupby(['month', 'type'])['amount'].sum().reset_index()
                st.plotly_chart(px.bar(month_group, x='month', y='amount', color='type', barmode='group', title="歷史每月收支對比", color_discrete_map={'收入': '#00CC96', '支出': '#EF553B'}), use_container_width=True)
        else: st.info("尚無數據。")

    with tab3:
        if not df.empty:
            df['month_key'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
            for m in sorted(df['month_key'].unique(), reverse=True):
                with st.expander(f"📅 {m} 月份明細紀錄", expanded=(m == now.strftime('%Y-%m'))):
                    m_df = df[df['month_key'] == m].sort_values(by='date', ascending=False)
                    for _, row in m_df.iterrows():
                        col1, col2, col3, col4 = st.columns([2, 5, 3, 2])
                        col1.write(f"{row['date'].strftime('%m-%d')}")
                        col2.write(f"**{row['category']}** | {row['note']}")
                        color = "green" if row['type'] == "收入" else "red"
                        col3.markdown(f"**:{color}[${row['amount']:,.0f}]**")
                        # 操作按鈕
                        b1, b2 = col4.columns(2)
                        if b1.button("✏️", key=f"e_{row['id']}"): st.session_state.editing_id = row['id']; st.rerun()
                        if b2.button("🗑️", key=f"d_{row['id']}"): 
                            st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                            app.save_data(target_url); st.rerun()
        else: st.info("尚無資料。")
else:
    st.title("💰 歡迎使用雲端理財系統")
    st.warning("👈 請在左側選單選擇身份以開始載入帳本")
