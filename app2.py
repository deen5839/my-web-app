import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date, timedelta
import io
import uuid
import plotly.express as px

# 1. 網頁初始設定
st.set_page_config(
    page_title="個人理財數據帳本-本地隱私版", 
    page_icon="💰", 
    layout="wide"
)

# 2. 數據處理核心 (完全回歸本地存檔，保護隱私)
class WebAccounting:
    def __init__(self):
        # 定義本地存檔檔名
        self.data_file = "my_private_data.json"
        
        # 💡 初始化保險：確保 session_state 變數存在
        if 'records' not in st.session_state:
            st.session_state.records = self.load_data()
        
        if 'editing_id' not in st.session_state:
            st.session_state.editing_id = None

    def load_data(self):
        """從本地電腦檔案讀取數據"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 轉換為 DataFrame 確保金額格式正確再轉回 dict
                    df = pd.DataFrame(data)
                    if not df.empty:
                        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                        return df.to_dict('records')
                    return []
            except Exception as e:
                st.error(f"讀取本地檔案出錯: {e}")
                return []
        return []

    def save_data(self):
        """將數據存入本地電腦檔案"""
        try:
            # 儲存為 JSON 格式，這是最私密的本地存法
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(st.session_state.records, f, ensure_ascii=False, indent=4)
            st.toast("✅ 資料已安全存入本地電腦！", icon="💾")
            return True
        except Exception as e:
            st.error(f"本地存檔失敗: {e}")
            return False

    def add_or_update_record(self, r_date, r_type, amount, category, note):
        """處理新增或編輯數據"""
        if st.session_state.editing_id is not None:
            # 修改邏輯
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
            # 新增邏輯
            new_id = str(uuid.uuid4())[:8]
            st.session_state.records.append({
                'id': new_id, 
                'date': r_date.strftime('%Y-%m-%d'),
                'type': r_type, 
                'amount': amount, 
                'category': category, 
                'note': note
            })
        # 存檔至本地
        self.save_data()

# --- 初始化應用執行 ---
if 'app' not in st.session_state:
    st.session_state.app = WebAccounting()

if 'editing_id' not in st.session_state:
    st.session_state.editing_id = None

app = st.session_state.app

# 3. 側邊欄：搜尋與 Excel 導出
with st.sidebar:
    st.header("🔍 本地數據管理")
    search_query = st.text_input("關鍵字搜尋", placeholder="搜尋備註...", key="sidebar_search")
    
    st.divider()
    st.header("📊 導出 Excel")
    
    if st.session_state.records:
        export_df = pd.DataFrame(st.session_state.records)
        export_df = export_df[['date', 'type', 'category', 'amount', 'note']]
        export_df.columns = ['日期', '類型', '分類', '金額', '備註']
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False)
            
        st.download_button(
            label="📥 下載 Excel 備份",
            data=buffer.getvalue(),
            file_name=f"我的理財資料_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.info("尚無本地數據")

# 4. 數據處理 (過濾)
df = pd.DataFrame(st.session_state.records)
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    if search_query:
        df = df[df['note'].str.contains(search_query, na=False, case=False) | 
                df['category'].str.contains(search_query, na=False, case=False)]

# 5. UI 主介面
st.title("💰 個人理財數據帳本 (隱私保護版)")

# 台灣時區
taiwan_now = datetime.now() + timedelta(hours=8)
now_hour = taiwan_now.hour
if 5 <= now_hour < 12: greeting = "🌅 早上好！"
elif 12 <= now_hour < 18: greeting = "☀️ 下午好！"
else: greeting = "🌙 晚上好！辛苦了。"

st.info(f"{greeting} 資料目前僅儲存在您的本地電腦，具有最高隱私性。")
st.caption(f"🚀 本地版 v2.0 | 系統時間：{taiwan_now.strftime('%H:%M')} | 不使用雲端 API")
st.divider()

tab1, tab2, tab3 = st.tabs(["➕ 記帳與修正", "📊 數據分析", "📋 歷史明細"])

# --- Tab 1: 輸入 ---
with tab1:
    edit_data = None
    if st.session_state.editing_id:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"🔧 修改模式中")

    r_type = st.radio("類型", ["支出", "收入"], index=0 if not edit_data or edit_data['type'] == "支出" else 1, horizontal=True)
    with st.form("input_form", clear_on_submit=(st.session_state.editing_id is None)):
        col1, col2 = st.columns(2)
        with col1:
            r_date = st.date_input("日期", datetime.strptime(edit_data['date'], '%Y-%m-%d').date() if edit_data else date.today())
        with col2:
            amount = st.number_input("金額", min_value=0.0, value=float(edit_data['amount']) if edit_data else 0.0)
            cats = ['薪水', '獎金', '投資', '洗衣店營收', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '其他']
            category = st.selectbox("分類", cats)
        note = st.text_input("備註", value=edit_data['note'] if edit_data else "")
        if st.form_submit_button("🚀 儲存至本機", use_container_width=True):
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.rerun()

# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        st.subheader("💰 財務現況")
        c1, c2, c3 = st.columns(3)
        c1.metric("總收入", f"${df[df['type']=='收入']['amount'].sum():,.0f}")
        c2.metric("總支出", f"${df[df['type']=='支出']['amount'].sum():,.0f}")
        c3.metric("淨資產", f"${df[df['type']=='收入']['amount'].sum() - df[df['type']=='支出']['amount'].sum():,.0f}")
        
        st.divider()
        col_bar, col_pie = st.columns(2)
        with col_bar:
            st.plotly_chart(px.bar(df[df['type']=='收入'].groupby('category')['amount'].sum().reset_index(), x='category', y='amount', title="收入來源"), use_container_width=True)
        with col_pie:
            st.plotly_chart(px.pie(df[df['type']=='支出'].groupby('category')['amount'].sum().reset_index(), values='amount', names='category', title="支出比例", hole=0.3), use_container_width=True)
        
        st.divider()
        st.subheader("🎯 預算進度")
        budget = st.number_input("本月預算", value=15000)
        exp_sum = df[df['type']=='支出']['amount'].sum()
        st.progress(min(exp_sum/budget, 1.0))
        st.write(f"已使用: {exp_sum/budget*100:.1f}%")
    else:
        st.info("尚無數據")

# --- Tab 3: 明細 ---
with tab3:
    if not df.empty:
        for _, row in df.sort_values(by=['date'], ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} | ${row['amount']}"):
                st.write(f"📝 備註: {row['note']}")
                ec1, ec2 = st.columns(2)
                if ec1.button("✏️ 修改", key=f"e_{row['id']}"):
                    st.session_state.editing_id = row['id']; st.rerun()
                if ec2.button("🗑️ 刪除", key=f"d_{row['id']}"):
                    st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                    app.save_data(); st.rerun()
