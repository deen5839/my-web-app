import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import uuid
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 網頁初始設定
# ==========================================
st.set_page_config(page_title="雲端理財旗艦版", page_icon="💰", layout="wide")

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
        if "records" not in st.session_state:
            st.session_state.records = []
        if "editing_id" not in st.session_state:
            st.session_state.editing_id = None

    def load_data(self, sheet_url=None):
        if not self.is_connected or not sheet_url:
            return []
        try:
            # 💡 關鍵修正：強制清除快取 ttl=0，確保切換帳號時一定會抓取對應試算表
            df = self.conn.read(
                spreadsheet=sheet_url, worksheet="Sheet1", ttl=0
            )
            if df is not None and not df.empty:
                # 確保必要欄位存在
                for col in ["id", "date", "type", "amount", "category", "note"]:
                    if col not in df.columns:
                        df[col] = ""

                # 處理缺失值，防止轉型失敗
                df["amount"] = (
                    pd.to_numeric(df["amount"], errors="coerce")
                    .fillna(0)
                    .astype(float)
                )
                df["date"] = df["date"].fillna(
                    datetime.now().strftime("%Y-%m-%d")
                )
                df["type"] = df["type"].fillna("支出")
                df["category"] = df["category"].fillna("其他")
                df["note"] = df["note"].fillna("")

                st.session_state.records = df.to_dict("records")
            else:
                st.session_state.records = []
            return st.session_state.records
        except Exception as e:
            st.error(f"⚠️ 讀取資料失敗：{e}")
            st.session_state.records = []
            return []

    def save_data(self, sheet_url=None):
        if not sheet_url:
            url_id = st.query_params.get("s")
            if url_id:
                sheet_url = (
                    f"https://docs.google.com/spreadsheets/d/{url_id}/edit"
                )

        if not self.is_connected or not sheet_url:
            st.error("❌ 寫入失敗：無法取得試算表網址！")
            return False
        try:
            df = (
                pd.DataFrame(st.session_state.records)
                if st.session_state.records
                else pd.DataFrame(
                    columns=["id", "date", "type", "amount", "category", "note"]
                )
            )
            # 強制將 Dataframe 轉為字串與數值乾淨格式
            self.conn.update(
                spreadsheet=sheet_url, worksheet="Sheet1", data=df
            )
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
        return self.save_data(sheet_url)

# 🔑 全域預先實例化，防止 NameError
if 'app' not in st.session_state: 
    st.session_state.app = CloudAccounting()
app = st.session_state.app

# ==========================================
# 3. 登入與側邊欄
# ==========================================
params = st.query_params
url_id = params.get("s")
auto_url = f"https://docs.google.com/spreadsheets/d/{url_id}/edit" if url_id else None

FRIENDS_DB = {
    "管理員 (本人)": {"id": "1dKLbifoTDOgeUPWasPmcbgl4wLu0_V6hHnCpropVs4k", "pin": "0526"},
    "哥哥": {"id": "1-ADQndfjfNASx8hKFdSlAOU7w7StaZSmfjJKQJqH6Fw", "pin": "0000"},
    "同學": {"id": "1BmnlohJ59OtuqQ5tCE8xZshIUmRan_4V4TPSRaTJqjg", "pin": "1111"},
    "DEEN": {"id": "1qnZFy57PcP9E0wbsMLA94-50odiORi7RJ6pXGFTZxiI", "pin": "7159"},
}

target_url = auto_url

with st.sidebar:
    st.header("🔐 系統登入")
    
    if auto_url:
        target_url = auto_url
        if st.button("🚪 登出系統"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()
    else:
        user_choice = st.selectbox("身份：", ["---"] + list(FRIENDS_DB.keys()))
        if user_choice in FRIENDS_DB:
            user_pin = st.text_input("通行碼", type="password")
            if user_pin == FRIENDS_DB[user_choice]["pin"]:
                st.query_params["s"] = FRIENDS_DB[user_choice]['id']
                st.rerun()
    
    st.divider()
    
    if st.button("🔄 刷新雲端資料"): 
        if target_url:
            app.load_data(target_url)
            st.toast("✅ 快取已更新！")
            st.rerun()
        else:
            st.warning("請先登入！")
    
    search_query = st.text_input("🔍 搜尋歷史紀錄", placeholder="搜尋分類、金額或備註")
    
    if st.session_state.records:
        csv = pd.DataFrame(st.session_state.records).to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載 CSV 備份", data=csv, file_name=f"finance_{date.today()}.csv")

# ==========================================
# 4. 主介面顯示
# ==========================================
if 'budget' not in st.session_state:
    st.session_state.budget = 30000.0

if target_url:
    if not st.session_state.records: 
        app.load_data(target_url)
    
    df = pd.DataFrame(st.session_state.records)
    
    if not df.empty and search_query:
        df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
        
    st.title("💰 雲端理財記帳本")
    tw_now = datetime.now() + timedelta(hours=8)
    curr_hour = tw_now.hour

    if 5 <= curr_hour < 12: msg = "🌅 早上好！今日又是數據力爆棚的一天。"
    elif 12 <= curr_hour < 18: msg = "☀️ 下午好！工作辛苦了，記得適時休息。"
    else: msg = "🌙 晚上好！整理完今日收支，早點休息。"

    st.info(f"{msg}")
    st.caption(f"🚀 穩定版 v2.8 | 系統時間：{tw_now.strftime('%H:%M')} | 隱私保護架構")
    st.divider()
    
    tab1, tab2, tab3 = st.tabs(["➕ 快速記帳", "📈 數據分析", "📋 歷史明細"])

    # --- Tab 1: 記帳 ---
    with tab1:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
        if edit_item:
            st.warning(f"📝 正在編輯紀錄 ID: {st.session_state.editing_id}")
        
        r_type_idx = 0 if not edit_item or edit_item['type'] == "支出" else 1
        r_type = st.radio("收支類型", ["支出", "收入"], index=r_type_idx, horizontal=True)
        
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                default_date = datetime.strptime(edit_item['date'], '%Y-%m-%d').date() if edit_item else date.today()
                r_date = st.date_input("日期", default_date)
            with c2:
                r_amount = st.number_input("金額", min_value=0.0, value=float(edit_item['amount']) if edit_item else 0.0)
                cats = ['薪水', '獎金', '投資', '發票', '房租', '洗衣店', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '信用卡', '瓦斯', '其他', '生活費', '電費', '水費', '職業工會']
                try: cat_idx = cats.index(edit_item['category']) if edit_item and edit_item['category'] in cats else 0
                except: cat_idx = 0
                r_cat = st.selectbox("分類", cats, index=cat_idx)
            
            r_note = st.text_input("詳細備註", value=edit_item['note'] if edit_item else "")
            
            btn_col1, btn_col2 = st.columns(2)
            if btn_col1.form_submit_button("🚀 同步至雲端", use_container_width=True):
                if r_amount > 0:
                    # 🔑 這裡強制將 target_url 傳入
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()
                else:
                    st.warning("⚠️ 金額必須大於 0 才可以寫入喔！")
            
            if edit_item:
                if btn_col2.form_submit_button("❌ 取消編輯", use_container_width=True):
                    st.session_state.editing_id = None
                    st.rerun()

    # --- Tab 2: 數據分析 ---
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
            
            if 'budget_input_v2' not in st.session_state:
                st.session_state.budget_input_v2 = 90000.0

            st.number_input("設定每月預算上限：", min_value=1000.0, step=1000.0, key="budget_input_v2")
            st.session_state.budget = st.session_state.budget_input_v2
            
            progress = min(this_month_ex / st.session_state.budget, 1.0)
            st.progress(progress)
            st.write(f"本月已花費: **${this_month_ex:,.0f}** / 預算: **${st.session_state.budget:,.0f}** ({progress*100:.1f}%)")

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
                curr_year_df = df[df['date_obj'].dt.year == now.year]
                if not curr_year_df.empty:
                    month_group = curr_year_df.groupby(['month_key', 'type'])['amount'].sum().reset_index()
                    st.plotly_chart(px.bar(month_group, x='month_key', y='amount', color='type', barmode='group', 
                                           title=f"{now.year} 當年收支趨勢對比", color_discrete_map={'收入':'#2ca02c', '支出':'#d62728'}), use_container_width=True)
                else: st.info(f"{now.year} 年尚無收支紀錄")
            
            st.subheader(f"📈 {selected_month} 每日資產成長曲線")
            df['net_val'] = df.apply(lambda x: x['amount'] if x['type'] == '收入' else -x['amount'], axis=1)
            daily_df = df.groupby('date_obj')['net_val'].sum().reset_index().sort_values('date_obj')
            daily_df['cumulative'] = daily_df['net_val'].cumsum()
            daily_df['month_key'] = daily_df['date_obj'].dt.strftime('%Y-%m')
            m_daily_df = daily_df[daily_df['month_key'] == selected_month]
            
            if not m_daily_df.empty:
                st.plotly_chart(px.line(m_daily_df, x='date_obj', y='cumulative', markers=True, title=f"{selected_month} 總資產變化"), use_container_width=True)
            else: st.info("該月尚無資料可繪製曲線")

    # --- Tab 3: 明細 ---
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
