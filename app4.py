import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import uuid
# 引入雲端連線模組
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 網頁初始設定 (Web Config)
# ==========================================
st.set_page_config(
    page_title="個人理財雲端帳本",
    page_icon="💰",
    layout="wide"
)

# ==========================================
# 2. 核心邏輯：雲端載體控制器
# ==========================================
class CloudAccounting:
    def __init__(self):
        # 建立與 Google Sheets 的安全連線
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.is_connected = True
        except Exception as e:
            st.error(f"⚠️ 雲端連線模組初始化失敗：{e}")
            self.is_connected = False

        # 初始化 Session State (本地暫存)
        if 'records' not in st.session_state:
            st.session_state.records = []
        
        if 'editing_id' not in st.session_state:
            st.session_state.editing_id = None

    def load_data(self, sheet_url=None):
        """從雲端載體讀取數據 (Read)"""
        if not self.is_connected:
            return []
            
        try:
            # 若有指定網址則讀取該網址，否則讀取 secrets 預設值
            df = self.conn.read(
                spreadsheet=sheet_url if sheet_url else None,
                worksheet="Sheet1",
                ttl=0  # ttl=0 確保不快取，即時更新
            )
            
            if df is not None and not df.empty:
                # 確保金額欄位為數字格式
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                # 轉換為列表格式存入 Session
                st.session_state.records = df.to_dict('records')
                return st.session_state.records
        except Exception as e:
            # 若讀取失敗 (例如試算表是空的)，回傳空列表但不報錯
            st.toast(f"ℹ️ 雲端載體初始化或為空", icon="☁️")
        return []

    def save_data(self, sheet_url=None):
        """將數據寫回雲端載體 (Write)"""
        if not self.is_connected:
            st.error("無法連線至雲端")
            return False

        try:
            if not st.session_state.records:
                # 若無資料，建立空 DataFrame
                df = pd.DataFrame(columns=['id', 'date', 'type', 'amount', 'category', 'note'])
            else:
                df = pd.DataFrame(st.session_state.records)

            # 執行雲端更新
            self.conn.update(
                spreadsheet=sheet_url if sheet_url else None,
                worksheet="Sheet1",
                data=df
            )
            st.toast("✅ 數據已安全同步至雲端！", icon="☁️")
            return True
        except Exception as e:
            st.error(f"❌ 雲端寫入失敗：{e}")
            return False

    def add_or_update(self, r_date, r_type, amount, category, note, sheet_url=None):
        """處理新增與修改邏輯"""
        # 1. 修改現有資料
        if st.session_state.editing_id is not None:
            for r in st.session_state.records:
                if r['id'] == st.session_state.editing_id:
                    r.update({
                        'date': r_date.strftime('%Y-%m-%d'),
                        'type': r_type,
                        'amount': amount,
                        'category': category,
                        'note': note
                    })
                    break
            st.session_state.editing_id = None
            
        # 2. 新增全新資料
        else:
            new_id = str(uuid.uuid4())[:8]
            st.session_state.records.append({
                'id': new_id,
                'date': r_date.strftime('%Y-%m-%d'),
                'type': r_type,
                'amount': amount,
                'category': category,
                'note': note
            })
            
        # 3. 立即同步
        self.save_data(sheet_url)

# --- 初始化應用實體 ---
if 'app' not in st.session_state:
    st.session_state.app = CloudAccounting()

app = st.session_state.app

# ==========================================
# 3. 側邊欄：隱私設定與資料管理
# ==========================================
with st.sidebar:
    st.header("🛡️ 載體隱私設定")
    
    # 隱私功能：允許使用者輸入自己的試算表網址
    st.info("預設連結至主帳本，若要切換隱私空間請在下方輸入網址。")
    custom_url = st.text_input("🔗 指定 Google Sheets 網址 (選填)", placeholder="https://docs.google.com/...")
    
    # 決定使用的目標網址
    target_url = custom_url if custom_url.strip() else None
    
    # 重新讀取按鈕 (強制同步)
    if st.button("🔄 強制讀取雲端資料"):
        app.load_data(target_url)
        st.rerun()

    st.divider()
    st.header("🔍 本地篩選")
    search_query = st.text_input("搜尋備註...", placeholder="例如：午餐")

# ==========================================
# 4. 程式啟動與數據載入
# ==========================================
# 每次畫面刷新時，確保數據是最新的 (防止手機端資料不同步)
if not st.session_state.records:
    app.load_data(target_url)

df = pd.DataFrame(st.session_state.records)

# 執行搜尋過濾
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    if search_query:
        df = df[df['note'].str.contains(search_query, na=False, case=False)]

# ==========================================
# 5. UI 主畫面與戰鬥儀表板
# ==========================================
st.title("💰 個人理財雲端帳本 (隱私強化版)")

# 台灣時間校正
tw_time = datetime.now() + timedelta(hours=8)
hour = tw_time.hour

if 5 <= hour < 12:
    msg = "🌅 早上好！雲端連線正常，數據同步中。"
elif 12 <= hour < 18:
    msg = "☀️ 下午好！喝口水，保持身心載體最佳狀態。"
else:
    msg = "🌙 晚上好！辛苦了，讓數據幫你記住生活。"

st.info(f"{msg}")
st.caption(f"🚀 超級賽亞人版 v3.0 | 系統時間：{tw_time.strftime('%H:%M')} | 狀態：{'🟢 已連線' if app.is_connected else '🔴 斷線'}")
st.divider()

# 分頁架構
tab1, tab2, tab3 = st.tabs(["➕ 雲端記帳", "📊 戰力分析", "📋 歷史檔案"])

# --- Tab 1: 記帳輸入區 ---
with tab1:
    # 檢查編輯狀態
    edit_item = None
    if st.session_state.editing_id:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"🔧 正在修改雲端數據 (ID: {st.session_state.editing_id})")

    r_type = st.radio("類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
    
    with st.form("entry_form", clear_on_submit=(not st.session_state.editing_id)):
        c1, c2 = st.columns(2)
        with c1:
            d_val = datetime.strptime(edit_item['date'], '%Y-%m-%d').date() if edit_item else date.today()
            r_date = st.date_input("日期", d_val)
        with c2:
            amt_val = float(edit_item['amount']) if edit_item else 0.0
            r_amount = st.number_input("金額", min_value=0.0, step=10.0, value=amt_val)
            
            # 分類選單
            inc_cats = ['薪水', '獎金', '投資', '其他']
            exp_cats = ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
            cats = inc_cats if r_type == '收入' else exp_cats
            
            # 自動對齊分類索引
            idx = 0
            if edit_item and edit_item['category'] in cats:
                idx = cats.index(edit_item['category'])
            r_cat = st.selectbox("分類", cats, index=idx)
            
        r_note = st.text_input("備註", value=edit_item['note'] if edit_item else "")
        
        # 提交按鈕
        if st.form_submit_button("🚀 同步至 Google Sheets", use_container_width=True):
            if r_amount > 0:
                app.add_or_update(r_date, r_type, r_amount, r_cat, r_note, target_url)
                st.rerun()

# --- Tab 2: 視覺化戰力分析 ---
with tab2:
    if not df.empty:
        total_in = df[df['type'] == '收入']['amount'].sum()
        total_ex = df[df['type'] == '支出']['amount'].sum()
        
        st.subheader("💰 財務戰力指標")
        m1, m2, m3 = st.columns(3)
        m1.metric("總收入", f"${total_in:,.0f}")
        m2.metric("總支出", f"${total_ex:,.0f}", delta=f"-{total_ex:,.0f}", delta_color="inverse")
        m3.metric("淨資產", f"${total_in - total_ex:,.0f}")
        
        st.divider()
        
        # 預算進度條 (你的最愛)
        st.subheader("🎯 預算防禦網")
        budget = st.number_input("本月預算上限", value=15000, step=500)
        # 簡單計算總支出比例 (可進階改為當月)
        prog = min(total_ex / budget, 1.0)
        
        cp, cv = st.columns([4, 1])
        with cp:
            st.progress(prog)
        with cv:
            st.write(f"**{prog*100:.1f}%**")
        st.write(f"📊 消耗狀態：**${total_ex:,.0f}** / ${budget:,.0f}")
        
        st.divider()
        
        # 雙圖表：收入長條圖 & 支出圓餅圖
        g1, g2 = st.columns(2)
        with g1:
            in_df = df[df['type'] == '收入']
            if not in_df.empty:
                fig_bar = px.bar(
                    in_df.groupby('category')['amount'].sum().reset_index(),
                    x='category', y='amount', title="收入來源分布", color='category'
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("尚無收入數據")
                
        with g2:
            ex_df = df[df['type'] == '支出']
            if not ex_df.empty:
                fig_pie = px.pie(
                    ex_df.groupby('category')['amount'].sum().reset_index(),
                    values='amount', names='category', title="支出類別占比", hole=0.3
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("尚無支出數據")
    else:
        st.info("☁️ 雲端載體目前為空，請開始第一筆記帳！")

# --- Tab 3: 歷史紀錄 (含刪除/修改) ---
with tab3:
    if not df.empty:
        for _, row in df.sort_values(by='date', ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - ${row['amount']:,.0f}"):
                st.write(f"📝 備註: {row['note']}")
                b1, b2 = st.columns(2)
                
                if b1.button("✏️ 修改", key=f"e_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                    
                if b2.button("🗑️ 刪除", key=f"d_{row['id']}"):
                    # 雲端刪除邏輯：先從 session 移除，再整包回寫
                    st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                    app.save_data(target_url)
                    st.rerun()
    else:
        st.info("📋 尚無歷史紀錄")

# ==========================================
# 程式結束 (雲端隱私強化版 v3.0)
# ==========================================
