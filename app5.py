import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta # ✅ 零件領取處
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
# 3. 登入與側邊欄 (終極修正版)
# ==========================================
params = st.query_params
url_id = params.get("s")
auto_url = f"https://docs.google.com/spreadsheets/d/{url_id}/edit" if url_id else None

FRIENDS_DB = {
    "管理員 (本人)": {"id": "1dKLbifoTDOgeUPWasPmcbgl4wLu0_V6hHnCpropVs4k", "pin": "0526"},
    "哥哥": {"id": "1-ADQndfjfNASx8hKFdSlAOU7w7StaZSmfjJKQJqH6Fw", "pin": "0000"},
    "同學": {"id": "1BmnlohJ59OtuqQ5tCE8xZshIUmRan_4V4TPSRaTJqjg", "pin": "1111"},
}

target_url = None

with st.sidebar:
    st.header("🔐 系統登入")
    
    # 狀況 A：已登入 (網址有參數) -> 顯示登出按鈕
    if auto_url:
        target_url = auto_url
        if st.button("🚪 登出系統"):
            st.query_params.clear()   # 清除網址參數
            st.session_state.clear()  # 清除快取
            st.rerun()                # 重新整理

    # 狀況 B：未登入 -> 顯示輸入框
    else:
        user_choice = st.selectbox("身份：", ["---"] + list(FRIENDS_DB.keys()))
        
        if user_choice in FRIENDS_DB:
            user_pin = st.text_input("通行碼", type="password")
            
            # 🔑 關鍵修正：密碼正確後，強制寫入網址參數並重整
            if user_pin == FRIENDS_DB[user_choice]["pin"]:
                # 把 ID 寫入網址，讓程式以為你是用連結登入的
                st.query_params["s"] = FRIENDS_DB[user_choice]['id']
                st.rerun()  # 馬上重新整理，登出按鈕就會出現了！
    
    st.divider()
    
    # 下面這些功能，不管有沒有登入都要顯示
    if st.button("🔄 刷新雲端資料"): 
        app.load_data(target_url)
        st.rerun()
    
    # --- 搜尋功能 ---
    search_query = st.text_input("🔍 搜尋歷史紀錄", placeholder="搜尋分類、金額或備註")
    
    if st.session_state.records:
        csv = pd.DataFrame(st.session_state.records).to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載 CSV 備份", data=csv, file_name=f"finance_{date.today()}.csv")

# ==========================================
# 4. 主介面顯示 (優化部分)
# ==========================================

# 在 target_url 判斷後，先初始化預算
if 'budget' not in st.session_state:
    st.session_state.budget = 30000.0
if target_url:
    if not st.session_state.records: app.load_data(target_url)
    df = pd.DataFrame(st.session_state.records)
    
    # --- 關鍵字過濾邏輯 ---
    if not df.empty and search_query:
        df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
    st.title("💰 雲端理財記帳本")
    tw_now = datetime.now() + timedelta(hours=8)
    curr_hour = tw_now.hour

    if 5 <= curr_hour < 12:
        msg = "🌅 早上好！今日又是數據力爆棚的一天。"
    elif 12 <= curr_hour < 18:
        msg = "☀️ 下午好！工作辛苦了，記得適時休息。"
    else:
        msg = "🌙 晚上好！整理完今日收支，早點休息。"

    st.info(f"{msg}")
    st.caption(f"🚀 穩定版 v2.8 | 系統時間：{tw_now.strftime('%H:%M')} | 隱私保護架構")
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
            
            # 💡 修復重點：使用 key 來維持狀態，並用 on_change 確保數值正確存入 session_state
            if 'budget_input' not in st.session_state:
                st.session_state.budget_input = st.session_state.budget

            st.number_input(
                "設定每月預算上限：", 
                min_value=1000.0, 
                value=90000.0,  # <-- 加上這行設定初始值為 90000 元
                step=1000.0, 
                key="budget_input"
            )
            # 將輸入值同步到全域預算變數
            st.session_state.budget = st.session_state.budget_input
            
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
                # 💡 修改重點：只過濾出當年前 (2026) 的資料進行月份對比
                curr_year_df = df[df['date_obj'].dt.year == now.year]
                if not curr_year_df.empty:
                    month_group = curr_year_df.groupby(['month_key', 'type'])['amount'].sum().reset_index()
                    st.plotly_chart(px.bar(month_group, x='month_key', y='amount', color='type', barmode='group', 
                                           title=f"{now.year} 當年收支趨勢對比", color_discrete_map={'收入':'#2ca02c', '支出':'#d62728'}), use_container_width=True)
                else:
                    st.info(f"{now.year} 年尚無收支紀錄")
            
            st.subheader(f"📈 {selected_month} 每日資產成長曲線")
            
            # 1. 先算出全歷史「每一天」的淨值加總 (把同一天的好幾筆帳合併)
            df['net_val'] = df.apply(lambda x: x['amount'] if x['type'] == '收入' else -x['amount'], axis=1)
            daily_df = df.groupby('date_obj')['net_val'].sum().reset_index()
            daily_df = daily_df.sort_values('date_obj')
            
            # 2. 算出「歷史以來的總累計資產」(這樣起點才不會是 0)
            daily_df['cumulative'] = daily_df['net_val'].cumsum()
            
            # 3. 標記月份，並只過濾出你「下拉選單選到的那個月 (selected_month)」
            daily_df['month_key'] = daily_df['date_obj'].dt.strftime('%Y-%m')
            m_daily_df = daily_df[daily_df['month_key'] == selected_month]
            
            # 4. 畫圖！
            if not m_daily_df.empty:
                st.plotly_chart(px.line(m_daily_df, x='date_obj', y='cumulative', markers=True, title=f"{selected_month} 總資產變化"), use_container_width=True)
            else:
                st.info("該月尚無資料可繪製曲線")

    # --- Tab 1: 記帳 & Tab 3: 明細 (保持穩定) ---
    # --- Tab 1: 記帳 (優化編輯內容保留 & 新增取消按鈕) ---
    with tab1:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
        
        if edit_item:
            st.warning(f"📝 正在編輯紀錄 ID: {st.session_state.editing_id}")
        
        # 判定類型
        r_type_idx = 0 if not edit_item or edit_item['type'] == "支出" else 1
        r_type = st.radio("收支類型", ["支出", "收入"], index=r_type_idx, horizontal=True)
        
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                # 1. 日期優化：編輯時自動帶入原日期
                default_date = datetime.strptime(edit_item['date'], '%Y-%m-%d').date() if edit_item else date.today()
                r_date = st.date_input("日期", default_date)
            with c2:
                r_amount = st.number_input("金額", min_value=0.0, value=float(edit_item['amount']) if edit_item else 0.0)
                
                # 2. 分類優化：編輯時自動帶入原分類
                cats = ['薪水', '獎金', '投資', '發票', '房租', '洗衣店', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '瓦斯', '其他', '電費', '水費', '職業工會']
                try:
                    cat_idx = cats.index(edit_item['category']) if edit_item and edit_item['category'] in cats else 0
                except ValueError:
                    cat_idx = 0
                r_cat = st.selectbox("分類", cats, index=cat_idx)
            
            r_note = st.text_input("詳細備註", value=edit_item['note'] if edit_item else "")
            
            # 3. 按鈕優化：同步與取消
            btn_col1, btn_col2 = st.columns(2)
            if btn_col1.form_submit_button("🚀 同步至雲端", use_container_width=True):
                if r_amount > 0:
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()
            
            if edit_item:
                if btn_col2.form_submit_button("❌ 取消編輯", use_container_width=True):
                    st.session_state.editing_id = None
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
