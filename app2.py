import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date, timedelta
import io
import uuid
import plotly.express as px
# --- 1. 新增雲端連接庫 ---
from streamlit_gsheets import GSheetsConnection

# 1. 網頁初始設定
st.set_page_config(
    page_title="個人理財數據帳本", 
    page_icon="💰", 
    layout="wide"
)

# 2. 數據處理核心 (升級為 Google Sheets 版)
class WebAccounting:
    def __init__(self):
        # 雲端試算表網址
        self.sheet_url = "https://docs.google.com/spreadsheets/d/1wc7rLawk5i6gfMEFw8p9hK_gUFlUIvCuL6-FPETNsw8/edit"
        
        try:
            # 建立與 Google Sheets 的連線
            self.conn = st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            st.error(f"❌ 雲端連接初始化失敗: {e}")
        
        # 💡 初始化保險：確保 session_state 變數絕對存在，防止介面崩潰
        if 'records' not in st.session_state:
            st.session_state.records = self.load_data()
        
        if 'editing_id' not in st.session_state:
            st.session_state.editing_id = None

    def load_data(self):
        """讀取雲端載體數據"""
        try:
            # 強制 ttl=0 以獲取最新數據
            df = self.conn.read(spreadsheet=self.sheet_url, worksheet="Sheet1", ttl=0)
            if df is not None and not df.empty:
                # 確保金額格式為數字
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                return df.to_dict('records')
        except:
            # 若連線失敗，回傳空清單，不中斷程式
            pass
        return []

    def save_data(self):
        """同步數據至雲端載體"""
        try:
            if not st.session_state.records:
                df = pd.DataFrame(columns=['id', 'date', 'type', 'amount', 'category', 'note'])
            else:
                df = pd.DataFrame(st.session_state.records)
            
            # 清除快取並上傳
            st.cache_data.clear()
            self.conn.update(
                spreadsheet=self.sheet_url, 
                worksheet="Sheet1", 
                data=df
            )
            st.cache_data.clear()
            st.toast("✅ 數據已成功同步至雲端載體！", icon="☁️")
            return True
        except Exception as e:
            # 顯示連線攔截訊息，提醒使用者下載備份
            st.sidebar.error(f"⚠️ 雲端寫入攔截（請下載 Excel 備份）：{e}")
            return False

    def add_or_update_record(self, r_date, r_type, amount, category, note):
        """處理新增或編輯數據"""
        if st.session_state.editing_id is not None:
            # 編輯模式：更新現有資料
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
        else:
            # 新增模式：產生唯一 ID
            new_id = str(uuid.uuid4())[:8]
            st.session_state.records.append({
                'id': new_id, 
                'date': r_date.strftime('%Y-%m-%d'),
                'type': r_type, 
                'amount': amount, 
                'category': category, 
                'note': note
            })
        
        # 每次更動後存檔
        self.save_data()

# --- 初始化應用執行 ---
if 'app' not in st.session_state:
    st.session_state.app = WebAccounting()

# 確保 editing_id 變數存在，防止 UI 渲染噴錯
if 'editing_id' not in st.session_state:
    st.session_state.editing_id = None

app = st.session_state.app

# 3. 側邊欄：搜尋與 Excel 導出
with st.sidebar:
    st.header("🔍 數據管理系統")
    search_query = st.text_input("關鍵字搜尋", placeholder="搜尋備註或分類...", key="sidebar_search")
    
    st.divider()
    st.header("📊 數據備份導出")
    
    if st.session_state.records:
        export_df = pd.DataFrame(st.session_state.records)
        export_df = export_df[['date', 'type', 'category', 'amount', 'note']]
        export_df.columns = ['日期', '類型', '分類', '金額', '備註']
        
        buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='記帳明細')
            
            st.download_button(
                label="📥 下載 Excel 備份檔",
                data=buffer.getvalue(),
                file_name=f"理財記錄_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error("Excel 檔案產生失敗")
    else:
        st.info("尚無數據可供導出備份")

# 4. 數據分析預處理
df = pd.DataFrame(st.session_state.records)
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    if search_query:
        df = df[
            df['note'].str.contains(search_query, na=False, case=False) | 
            df['category'].str.contains(search_query, na=False, case=False)
        ]

# 5. UI 主介面設計
st.title("💰 個人理財數據載體帳本")

# 台灣時區校正 (UTC+8)
taiwan_now = datetime.now() + timedelta(hours=8)
now_hour = taiwan_now.hour

if 5 <= now_hour < 12:
    greeting = "🌅 早上好！今天也是充滿數據力的一天。"
elif 12 <= now_hour < 18:
    greeting = "☀️ 下午好！南科陽光正美，記得多喝水喔。"
else:
    greeting = "🌙 晚上好！辛苦了，早點休息，明早鑑定加油。"

st.info(f"{greeting}")
st.caption(f"🚀 雲端載體 v1.5 | 系統時間：{taiwan_now.strftime('%H:%M')} | 核心庫：Streamlit-GSheets")
st.divider()

tab1, tab2, tab3 = st.tabs(["➕ 記帳與修正", "📊 數據趨勢分析", "📋 歷史明細清單"])

# --- Tab 1: 數據輸入 ---
with tab1:
    edit_data = None
    if st.session_state.editing_id:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"🔧 正在修改數據 ID: {st.session_state.editing_id}")

    r_type = st.radio("收支類型", ["支出", "收入"], index=0 if not edit_data or edit_data['type'] == "支出" else 1, horizontal=True)

    with st.form("input_form", clear_on_submit=(st.session_state.editing_id is None)):
        col1, col2 = st.columns(2)
        with col1:
            default_date = date.today()
            if edit_data:
                try: default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
                except: default_date = date.today()
            r_date = st.date_input("選擇日期", default_date)
            
        with col2:
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=10.0, value=float(edit_data['amount']) if edit_data else 0.0)
            income_cats = ['薪水', '獎金', '投資', '洗衣店收入', '其他']
            expense_cats = ['飲食', '交通', '購物', '醫療', '娛樂', '訂閱', '其他']
            categories = income_cats if r_type == '收入' else expense_cats
            cat_idx = 0
            if edit_data and edit_data['category'] in categories:
                cat_idx = categories.index(edit_data['category'])
            category = st.selectbox("分類標籤", categories, index=cat_idx)

        note = st.text_input("備註說明", value=edit_data['note'] if edit_data else "", placeholder="例如：7-11 咖啡...")
        
        submit_btn = st.form_submit_button("🚀 同步至雲端載體", use_container_width=True)
        
        if submit_btn:
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.success("☁️ 數據處理成功！")
                st.rerun()

# --- Tab 2: 統計圖表 ---
with tab2:
    if not df.empty:
        total_income = df[df['type'] == '收入']['amount'].sum()
        total_expense = df[df['type'] == '支出']['amount'].sum()
        
        st.subheader("💰 財務現況統計")
        c1, c2, c3 = st.columns(3)
        c1.metric("總收入", f"${total_income:,.0f}")
        c2.metric("總支出", f"${total_expense:,.0f}", delta=f"-{total_expense:,.0f}", delta_color="inverse")
        c3.metric("淨資產", f"${total_income - total_expense:,.0f}")
        
        st.divider()
        st.subheader("📊 收支分布對照圖")
        col_bar, col_pie = st.columns(2)
        
        with col_bar:
            # 補回：收入來源長條圖
            income_df = df[df['type'] == '收入']
            if not income_df.empty:
                fig_bar = px.bar(income_df.groupby('category')['amount'].sum().reset_index(), 
                                 x='category', y='amount', title="收入來源占比", color='category')
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("尚無收入數據可顯示長條圖")

        with col_pie:
            # 支出圓餅圖
            expense_df = df[df['type'] == '支出']
            if not expense_df.empty:
                fig_pie = px.pie(expense_df.groupby('category')['amount'].sum().reset_index(), 
                                 values='amount', names='category', title="支出類別分布", hole=0.3)
                st.plotly_chart(fig_pie, use_container_width=True)
        
        st.divider()
        st.subheader("🎯 預算進度監控")
        budget = st.number_input("設定本月支出預算", min_value=1000, value=15000)
        this_month_exp = df[(df['type']=='支出') & (pd.to_datetime(df['date']).dt.month == taiwan_now.month)]['amount'].sum()
        progress = min(this_month_exp / budget, 1.0)
        st.write(f"本月已用：**${this_month_exp:,.0f}** / ${budget:,.0f}")
        st.progress(progress)
    else:
        st.info("📊 載體內尚無數據，請先記帳。")

# --- Tab 3: 歷史明細 ---
with tab3:
    if not df.empty:
        for _, row in df.sort_values(by=['date'], ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"📝 備註: {row['note']}")
                ec1, ec2 = st.columns(2)
                if ec1.button("✏️ 修改數據", key=f"edit_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if ec2.button("🗑️ 刪除紀錄", key=f"del_{row['id']}"):
                    st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                    app.save_data()
                    st.rerun()
    else:
        st.info("📋 尚無歷史紀錄，快去記一筆吧！")
