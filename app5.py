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
        if not self.is_connected or not sheet_url: 
            return []
        try:
            df = self.conn.read(spreadsheet=sheet_url, worksheet="Sheet1", ttl=0)
            if df is not None and not df.empty:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                st.session_state.records = df.to_dict('records')
                return st.session_state.records
        except Exception as e:
            st.error(f"🚨 讀取發生錯誤：{e}")
        return []

    def save_data(self, sheet_url=None):
        if not self.is_connected or not sheet_url: return False
        try:
            # 即使資料為空也允許更新（用於刪除最後一筆資料時）
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
# 3. 網址參數偵測與朋友資料庫
# ==========================================
params = st.query_params
url_id = params.get("s")
auto_url = f"https://docs.google.com/spreadsheets/d/{url_id}/edit" if url_id else None

FRIENDS_DB = {
    "管理員 (本人)": {"id": "1dKLbifoTDOgeUPWasPmcbgl4wLu0_V6hHnCpropVs4k", "pin": "5839"},
    "哥哥": {"id": "請填入哥哥的ID", "pin": "0000"},
}

# ==========================================
# 4. 側邊欄：登入與搜尋
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
        elif user_choice == "手動輸入網址 (訪客)":
            custom_url = st.text_input("🔗 請貼上您的試算表網址")
            if custom_url: target_url = custom_url

    if st.button("🔄 刷新/載入帳本"):
        st.session_state.records = []
        st.rerun()
    
    st.divider()
    search_query = st.text_input("🔍 搜尋歷史紀錄", placeholder="搜尋分類、金額或備註")

# ==========================================
# 5. 主介面顯示
# ==========================================
if target_url:
    if not st.session_state.records:
        app.load_data(target_url)
    
    df = pd.DataFrame(st.session_state.records)
    if not df.empty and search_query:
        df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

    tab1, tab2, tab3 = st.tabs(["➕ 快速記帳", "📊 數據分析", "📋 歷史明細"])

    # --- Tab 1: 記帳 (支援編輯模式) ---
    with tab1:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
        
        if edit_item:
            st.warning(f"🔧 正在修改紀錄 (ID: {st.session_state.editing_id})")
            if st.button("取消修改"):
                st.session_state.editing_id = None
                st.rerun()

        r_type = st.radio("收支類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            # 處理日期預設值
            try:
                default_date = datetime.strptime(edit_item['date'], '%Y-%m-%d').date() if edit_item else date.today()
            except:
                default_date = date.today()

            with c1: r_date = st.date_input("日期", default_date)
            with c2:
                r_amount = st.number_input("金額", min_value=0.0, step=10.0, value=float(edit_item['amount']) if edit_item else 0.0)
                cats = ['薪水', '獎金', '投資', '發票中獎', '洗衣店營收', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
                try:
                    cat_index = cats.index(edit_item['category']) if edit_item and edit_item['category'] in cats else 0
                except:
                    cat_index = 0
                r_cat = st.selectbox("項目分類", cats, index=cat_index)
            r_note = st.text_input("詳細備註", value=edit_item['note'] if edit_item else "")
            
            btn_label = "💾 儲存修改" if edit_item else "🚀 同步至雲端"
            if st.form_submit_button(btn_label, use_container_width=True):
                if r_amount > 0:
                    app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                    st.rerun()

    # --- Tab 2: 分析 ---
    with tab2:
        if not df.empty:
            st.subheader("💰 財務總覽")
            total_in = df[df['type'] == '收入']['amount'].sum()
            total_ex = df[df['type'] == '支出']['amount'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("累積總收入", f"${total_in:,.0f}")
            m2.metric("累積總支出", f"${total_ex:,.0f}", delta=f"-{total_ex:,.0f}", delta_color="inverse")
            m3.metric("淨收入 (餘額)", f"${total_in - total_ex:,.0f}")
            st.divider()
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.bar(df[df['type'] == '收入'].groupby('category')['amount'].sum().reset_index(), x='category', y='amount', title="收入來源", color='category'), use_container_width=True)
            with g2: st.plotly_chart(px.pie(df[df['type'] == '支出'].groupby('category')['amount'].sum().reset_index(), values='amount', names='category', title="支出占比", hole=0.3), use_container_width=True)
        else: st.info("尚無數據。")

            # --- 當月消費進度 ---
            st.subheader("🎯 當月消費進度")
            curr_month = datetime.now().strftime('%Y-%m')
            month_ex = df[(pd.to_datetime(df['date']).dt.strftime('%Y-%m') == curr_month) & (df['type'] == '支出')]['amount'].sum()
            budget = st.number_input("設定每月預算", min_value=1, value=20000)
            st.progress(min(month_ex/budget, 1.0))
            st.write(f"本月累計支出: **${month_ex:,.0f}** / ${budget:,.0f}")

            st.divider()

    # --- Tab 3: 明細 (新增編輯與刪除按鈕) ---
    with tab3:
        if not df.empty:
            # 建立月份清單
            df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
            months = sorted(df['month'].unique(), reverse=True)
            
            for m in months:
                with st.expander(f"📅 {m} 月份紀錄", expanded=True):
                    # 篩選該月資料
                    m_df = df[df['month'] == m].sort_values(by='date', ascending=False)
                    
                    # 標題列
                    h1, h2, h3, h4, h5 = st.columns([2, 2, 3, 2, 2])
                    h1.write("**日期**")
                    h2.write("**類別**")
                    h3.write("**備註**")
                    h4.write("**金額**")
                    h5.write("**操作**")
                    st.divider()

                    # 逐行顯示資料與按鈕
                    for _, row in m_df.iterrows():
                        col_date, col_cat, col_note, col_amt, col_act = st.columns([2, 2, 3, 2, 2])
                        col_date.write(row['date'])
                        col_cat.write(row['category'])
                        col_note.write(row['note'])
                        
                        # 收入顯示綠色，支出顯示紅色
                        color = "green" if row['type'] == "收入" else "red"
                        col_amt.write(f":{color}[${row['amount']:,.0f}]")
                        
                        # 操作按鈕
                        btn_col1, btn_col2 = col_act.columns(2)
                        # 編輯按鈕
                        if btn_col1.button("✏️", key=f"edit_{row['id']}"):
                            st.session_state.editing_id = row['id']
                            st.toast("請切換到『快速記帳』分頁進行修改")
                            st.rerun()
                        
                        # 刪除按鈕
                        if btn_col2.button("🗑️", key=f"del_{row['id']}"):
                            st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                            app.save_data(target_url)
                            st.rerun()
        else:
            st.info("尚無歷史明細。")
else:
    st.title("💰 歡迎使用雲端理財系統")
    st.warning("👈 請在左側選單選擇身份並輸入「通行碼」以載入帳本。")
