import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import uuid
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 網頁初始設定
# ==========================================
st.set_page_config(page_title="雲端理財系統專業版", page_icon="💰", layout="wide")

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
# 3. 側邊欄：身份切換與搜尋 (功能強化)
# ==========================================
target_url = None
with st.sidebar:
    st.header("🔐 App 設定與搜尋")
    try: robot_email = st.secrets["connections"]["gsheets"]["client_email"]
    except: robot_email = "請檢查 Secrets"

    user_type = st.radio("您的身份：", ["我是訪客", "我是管理員 (本人)"], index=0 if auto_url else 1)
    
    if user_type == "我是管理員 (本人)":
        pwd = st.text_input("🔑 密碼", type="password")
        if pwd == "5839":
            try: target_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            except: st.error("Secrets 缺少網址")
        else: st.warning("請輸入密碼")
    else:
        st.info("👋 專屬帳本模式")
        if auto_url:
            st.success("✅ 已自動載入您的帳本")
            target_url = auto_url
        else:
            st.code(robot_email, language="text")
            st.caption("1. 複製 Email 分享表格權限")
            custom_url = st.text_input("🔗 2. 貼上您的網址", placeholder="https://docs.google.com/...")
            if custom_url: 
                target_url = custom_url
                # --- 新增：魔法連結生成器 ---
                try:
                    # 從網址抓出 ID
                    sheet_id = custom_url.split("/d/")[1].split("/")[0]
                    # 取得目前 App 的主網址 (去網址參數)
                    base_url = st.get_option("browser.gatherUsageStats") # 這裡簡化處理
                    st.write("---")
                    st.success("✨ 成功連接！")
                    st.write("這是您的**專屬登入連結**，請存到 LINE 記事本，下次點開直接記帳：")
                    # 假設你的 app 網址是 your-app.streamlit.app
                    st.code(f"https://your-app.streamlit.app/?s={sheet_id}", language="text")
                except:
                    pass

    if st.button("🔄 同步數據"): st.rerun()
    
    st.divider()
    # --- 搜尋功能強化為「數據紀錄搜尋」 ---
    st.subheader("🔍 數據紀錄搜尋")
    search_query = st.text_input("搜尋關鍵字...", placeholder="可搜分類、備註、金額...")

# ==========================================
# 4. 數據處理與介面呈現
# ==========================================
if not st.session_state.records and target_url:
    app.load_data(target_url)

if not target_url:
    st.title("💰 個人雲端理財系統")
    st.markdown("### 🚀 同學/朋友快速上手指南")
    c1, c2, c3 = st.columns(3)
    with c1: st.info("**1. 準備帳本**\n\n建立 Google 表格，分頁改名為 `Sheet1`")
    with c2: st.info("**2. 分享權限**\n\n複製左側 Email，在表格按『共用』貼上")
    with c3: st.info("**3. 開始記帳**\n\n貼上表格網址，即可安全記帳！")
    st.divider()
    st.warning("👈 請從左側選單開始設定您的帳本路徑。")
else:
    df = pd.DataFrame(st.session_state.records)
    
    # --- 全域搜尋邏輯 (包含分類與備註) ---
    if not df.empty and search_query:
        # 將整行轉成字串，只要包含搜尋字就顯示
        df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

    st.title("💰 理財數據中心")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["➕ 快速記帳", "📊 數據分析", "📋 紀錄明細"])

    # --- Tab 1: 記帳 ---
    with tab1:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
        r_type = st.radio("收支類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
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
                r_cat = st.selectbox("項目分類", cats, index=cats.index(edit_item['category']) if edit_item and edit_item['category'] in cats else 0)
            r_note = st.text_input("詳細備註", value=edit_item['note'] if edit_item else "")
            if st.form_submit_button("🚀 確認同步", use_container_width=True):
                if r_amount > 0:
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()

    # --- Tab 2: 分析 ---
    with tab2:
        if not df.empty:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
            df['date_obj'] = pd.to_datetime(df['date'])
            
            # 預算系統
            st.subheader("🎯 當月消費防禦線")
            curr_month = datetime.now().strftime('%Y-%m')
            month_mask = (df['date_obj'].dt.strftime('%Y-%m') == curr_month)
            month_ex = df[month_mask & (df['type'] == '支出')]['amount'].sum()
            
            c_budget, c_info = st.columns([1, 2])
            with c_budget:
                budget = st.number_input("設定月預算", min_value=1, value=20000, step=1000)
            
            ratio = min(month_ex / budget, 1.0)
            percent = (month_ex / budget) * 100
            st.progress(ratio)
            
            if percent < 70: st.success(f"目前支出 ${month_ex:,.0f} ({percent:.1f}%)，進度安全！")
            elif percent < 90: st.warning(f"目前支出 ${month_ex:,.0f} ({percent:.1f}%)，請多節省。")
            else: st.error(f"⚠️ 支出 ${month_ex:,.0f} ({percent:.1f}%)，已接近破表！")
            
            st.divider()
            
            total_in = df[df['type'] == '收入']['amount'].sum()
            total_ex = df[df['type'] == '支出']['amount'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("累積總收入", f"${total_in:,.0f}")
            m2.metric("累積總支出", f"${total_ex:,.0f}", delta=f"-{total_ex:,.0f}", delta_color="inverse")
            m3.metric("目前淨餘額", f"${total_in - total_ex:,.0f}")
            
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.bar(df[df['type'] == '收入'].groupby('category')['amount'].sum().reset_index(), x='category', y='amount', title="收入來源比例", color='category'), use_container_width=True)
            with g2: st.plotly_chart(px.pie(df[df['type'] == '支出'].groupby('category')['amount'].sum().reset_index(), values='amount', names='category', title="支出結構分析", hole=0.3), use_container_width=True)
        else:
            st.info("☁️ 尚無歷史紀錄可供分析。")

    # --- Tab 3: 紀錄明細 (月份分組) ---
    with tab3:
        if not df.empty:
            df['date_obj'] = pd.to_datetime(df['date'])
            df['month_str'] = df['date_obj'].dt.strftime('%Y-%m')
            unique_months = sorted(df['month_str'].unique(), reverse=True)
            for m in unique_months:
                month_df = df[df['month_str'] == m].sort_values(by='date', ascending=False)
                m_in = month_df[month_df['type']=='收入']['amount'].sum()
                m_ex = month_df[month_df['type']=='支出']['amount'].sum()
                with st.expander(f"📅 {m} 數據統計 (盈餘: ${m_in - m_ex:,.0f})", expanded=(m == datetime.now().strftime('%Y-%m'))):
                    st.caption(f"本月收: ${m_in:,.0f} | 支: ${m_ex:,.0f}")
                    for _, row in month_df.iterrows():
                        col_date, col_info, col_amt, col_act = st.columns([2, 4, 2, 2])
                        with col_date: st.write(row['date'])
                        with col_info: st.write(f"[{row['category']}] {row['note']}")
                        with col_amt: 
                            c = "green" if row['type'] == "收入" else "red"
                            st.markdown(f":{c}[${row['amount']:,.0f}]")
                        with col_act:
                            c1, c2 = st.columns(2)
                            if c1.button("✏️", key=f"e_{row['id']}"): st.session_state.editing_id = row['id']; st.rerun()
                            if c2.button("🗑️", key=f"d_{row['id']}"): st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]; app.save_data(target_url); st.rerun()
        else:
            st.info("☁️ 找不到符合搜尋條件的紀錄。")
