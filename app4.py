import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import uuid
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 網頁初始設定
# ==========================================
st.set_page_config(page_title="個人理財雲端帳本", page_icon="💰", layout="wide")

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
        if not self.is_connected: return []
        try:
            # 若有指定網址則讀取該網址
            df = self.conn.read(spreadsheet=sheet_url if sheet_url else None, worksheet="Sheet1", ttl=0)
            if df is not None and not df.empty:
                # 確保金額是數字，日期是標準格式
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                st.session_state.records = df.to_dict('records')
                return st.session_state.records
        except Exception as e:
             # 靜默失敗或顯示輕微提示，避免嚇到使用者
            pass
        return []

    def save_data(self, sheet_url=None):
        if not self.is_connected: return False
        try:
            df = pd.DataFrame(st.session_state.records) if st.session_state.records else pd.DataFrame(columns=['id', 'date', 'type', 'amount', 'category', 'note'])
            self.conn.update(spreadsheet=sheet_url if sheet_url else None, worksheet="Sheet1", data=df)
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
# 3. 側邊欄：隱私設定
# ==========================================
with st.sidebar:
    st.header("🛡️ 載體隱私設定")
    # 優先嘗試從 secrets 讀取，沒有才用側邊欄
    try:
        secret_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    except:
        secret_url = ""
    
    if secret_url:
        st.success("已從 Secrets 讀取試算表網址")
        target_url = secret_url
    else:
        st.info("請輸入您的 Google Sheet 網址")
        custom_url = st.text_input("🔗 Google Sheets 網址", placeholder="https://docs.google.com/...")
        target_url = custom_url if custom_url.strip() else None
    
    if st.button("🔄 強制讀取"):
        app.load_data(target_url)
        st.rerun()
    st.divider()
    search_query = st.text_input("搜尋備註...", placeholder="例如：午餐")

# ==========================================
# 4. 數據載入與 UI
# ==========================================
if not st.session_state.records and target_url:
    app.load_data(target_url)

df = pd.DataFrame(st.session_state.records)

# 搜尋過濾
if not df.empty and search_query:
    df = df[df['note'].str.contains(search_query, na=False, case=False)]

st.title("💰 個人理財雲端帳本")
tw_time = datetime.now() + timedelta(hours=8)
st.caption(f"🚀 Python 3.11 穩定版 | 系統時間：{tw_time.strftime('%H:%M')}")
st.divider()

tab1, tab2, tab3 = st.tabs(["➕ 雲端記帳", "📊 戰力分析", "📋 歷史檔案"])

# --- Tab 1: 記帳 ---
with tab1:
    edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
    if edit_item: st.warning(f"🔧 修改中 ID: {st.session_state.editing_id}")
    r_type = st.radio("類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
    with st.form("entry_form", clear_on_submit=(not st.session_state.editing_id)):
        c1, c2 = st.columns(2)
        # 日期轉換防呆
        default_date = date.today()
        if edit_item:
            try:
                default_date = datetime.strptime(edit_item['date'], '%Y-%m-%d').date()
            except:
                pass
        
        with c1: r_date = st.date_input("日期", default_date)
        with c2:
            r_amount = st.number_input("金額", min_value=0.0, step=10.0, value=float(edit_item['amount']) if edit_item else 0.0)
            cats = ['薪水', '獎金', '投資', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
            # 分類防呆
            try:
                cat_index = cats.index(edit_item['category'])
            except:
                cat_index = 0
            r_cat = st.selectbox("分類", cats, index=cat_index if edit_item else 0)
        r_note = st.text_input("備註", value=edit_item['note'] if edit_item else "")
        if st.form_submit_button("🚀 同步至 Google Sheets", use_container_width=True):
            if not target_url: st.error("請先確認 Google Sheets 網址！")
            elif r_amount > 0:
                app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                st.rerun()

# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        # 確保金額是數字類型
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
            income_df = df[df['type'] == '收入']
            if not income_df.empty: 
                st.plotly_chart(px.bar(income_df.groupby('category')['amount'].sum().reset_index(), x='category', y='amount', title="收入來源", color='category'), use_container_width=True)
        with g2:
            expense_df = df[df['type'] == '支出']
            if not expense_df.empty: 
                st.plotly_chart(px.pie(expense_df.groupby('category')['amount'].sum().reset_index(), values='amount', names='category', title="支出占比", hole=0.3), use_container_width=True)
    else: st.info("☁️ 尚無資料，請先新增記帳")

# --- Tab 3: 歷史 (按月份分組升級版) ---
with tab3:
    if not df.empty:
        # 1. 建立月份欄位 'YYYY-MM'
        df['date_obj'] = pd.to_datetime(df['date'])
        df['month_str'] = df['date_obj'].dt.strftime('%Y-%m')
        
        # 2. 取得所有不重複的月份，並由新到舊排序
        unique_months = sorted(df['month_str'].unique(), reverse=True)
        
        # 3. 跑迴圈顯示每個月
        for m in unique_months:
            # 篩選該月份資料
            month_df = df[df['month_str'] == m].sort_values(by='date', ascending=False)
            
            # 計算該月收支
            m_in = month_df[month_df['type']=='收入']['amount'].sum()
            m_ex = month_df[month_df['type']=='支出']['amount'].sum()
            balance = m_in - m_ex
            
            # 顯示月份標題 (加上收支統計)
            with st.expander(f"📅 {m} 月結算 (餘額: ${balance:,.0f})", expanded=True):
                st.caption(f"收入: ${m_in:,.0f} | 支出: ${m_ex:,.0f}")
                
                # 顯示該月每一筆交易
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
                
    else:
        st.info("☁️ 尚無歷史資料")
