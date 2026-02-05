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
    page_title="個人理財數據帳本-隱私載體版", 
    page_icon="💰", 
    layout="wide"
)

# 2. 數據處理核心
class WebAccounting:
    def __init__(self):
        if 'records' not in st.session_state:
            st.session_state.records = []
        
        if 'editing_id' not in st.session_state:
            st.session_state.editing_id = None

    def save_data(self):
        st.toast("✅ 數據已寫入暫時載體，重新整理前請下載備份！", icon="💾")
        return True

    def add_or_update_record(self, r_date, r_type, amount, category, note):
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
        self.save_data()

# --- 初始化應用 ---
if 'app' not in st.session_state:
    st.session_state.app = WebAccounting()
app = st.session_state.app

# 3. 側邊欄：搜尋與隱私還原
with st.sidebar:
    st.header("🔍 數據管理")
    search_query = st.text_input("搜尋備註關鍵字...", placeholder="例如：加油")
    
    st.divider()
    st.header("📤 資料還原")
    uploaded_file = st.file_uploader("上傳 JSON 備份檔", type="json")
    if uploaded_file is not None:
        try:
            st.session_state.records = json.load(uploaded_file)
            st.success("✅ 資料已成功還原！")
        except:
            st.error("❌ 讀取失敗")

    st.divider()
    st.header("📥 下載備份")
    if st.session_state.records:
        json_str = json.dumps(st.session_state.records, ensure_ascii=False, indent=4)
        st.download_button(label="💾 下載 JSON 備份", data=json_str, file_name=f"備份_{date.today()}.json")
        
        df_exp = pd.DataFrame(st.session_state.records)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_exp.to_excel(writer, index=False)
        st.download_button(label="📊 導出 Excel 報表", data=buffer.getvalue(), file_name=f"報表_{date.today()}.xlsx")

# 4. 數據處理
df = pd.DataFrame(st.session_state.records)
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    if search_query:
        df = df[df['note'].str.contains(search_query, na=False, case=False)]

# 5. UI 主介面
st.title("💰 個人理財數據帳本 ")

taiwan_now = datetime.now() + timedelta(hours=8)
now_hour = taiwan_now.hour
if 5 <= now_hour < 12: greeting = "🌅 早上好！今日又是數據力爆棚的一天。"
elif 12 <= now_hour < 18: greeting = "☀️ 下午好！南科陽光正美，記得喝水。"
else: greeting = "🌙 晚上好！辛苦了，整理完早點休息。"

st.info(f"{greeting}")
st.caption(f"🚀 穩定版 v2.7 | 系統時間：{taiwan_now.strftime('%H:%M')} | 資料僅留存於瀏覽器與檔案")
st.divider()

tab1, tab2, tab3 = st.tabs(["➕ 數據記帳", "📊 數據趨勢分析", "📋 歷史明細"])

# --- Tab 1: 記帳 (修正分類對齊功能) ---
with tab1:
    edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None) if st.session_state.editing_id else None
    if edit_data: st.warning(f"🔧 正在修改數據 ID: {st.session_state.editing_id}")

    r_type = st.radio("收支類型", ["支出", "收入"], index=0 if not edit_data or edit_data['type'] == "支出" else 1, horizontal=True)
    
    with st.form("input_form", clear_on_submit=(not st.session_state.editing_id)):
        c_a, c_b = st.columns(2)
        with c_a:
            r_date = st.date_input("日期", datetime.strptime(edit_data['date'], '%Y-%m-%d').date() if edit_data else date.today())
        with c_b:
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=10.0, value=float(edit_data['amount']) if edit_data else 0.0)
            
            # 💡 核心修正：計算正確的分類索引
            cats = ['薪水', '獎金', '投資', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
            default_cat_idx = 0
            if edit_data and edit_data['category'] in cats:
                default_cat_idx = cats.index(edit_data['category'])
            
            category = st.selectbox("分類標籤", cats, index=default_cat_idx)
            
        note = st.text_input("備註說明", value=edit_data['note'] if edit_data else "")
        if st.form_submit_button("🚀 寫入本地載體", use_container_width=True):
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.rerun()

# --- Tab 2: 分析 (預算橫向進度條) ---
with tab2:
    if not df.empty:
        total_in = df[df['type'] == '收入']['amount'].sum()
        total_ex = df[df['type'] == '支出']['amount'].sum()
        st.subheader("💰 財務現況概覽")
        m1, m2, m3 = st.columns(3)
        m1.metric("總收入", f"${total_in:,.0f}")
        m2.metric("總支出", f"${total_ex:,.0f}", delta=f"-{total_ex:,.0f}", delta_color="inverse")
        m3.metric("淨資產", f"${total_in - total_ex:,.0f}")
        
        st.divider()
        st.subheader("🎯 本月預算執行進度")
        budget = st.number_input("💸 設定本月支出預算目標", min_value=1000, value=15000, step=500)
        percent = min(total_ex / budget, 1.0)
        
        col_prog, col_val = st.columns([4, 1])
        with col_prog:
            st.progress(percent)
        with col_val:
            st.write(f"**{percent*100:.1f}%**")
        st.write(f"📊 目前進度：**${total_ex:,.0f}** / ${budget:,.0f}")
        
        st.divider()
        col_left, col_right = st.columns(2)
        with col_left:
            in_df = df[df['type'] == '收入']
            if not in_df.empty:
                st.plotly_chart(px.bar(in_df.groupby('category')['amount'].sum().reset_index(), x='category', y='amount', title="收入來源占比", color='category'), use_container_width=True)
        with col_right:
            ex_df = df[df['type'] == '支出']
            if not ex_df.empty:
                st.plotly_chart(px.pie(ex_df.groupby('category')['amount'].sum().reset_index(), values='amount', names='category', title="支出類別分布", hole=0.3), use_container_width=True)
    else: st.info("📊 尚未有數據可進行分析。")

# --- Tab 3: 明細 ---
with tab3:
    if not df.empty:
        for _, row in df.sort_values(by='date', ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - ${row['amount']:,.0f}"):
                st.write(f"📝 備註: {row['note']}")
                ec1, ec2 = st.columns(2)
                if ec1.button("✏️ 修改", key=f"edit_{row['id']}"):
                    st.session_state.editing_id = row['id']; st.rerun()
                if ec2.button("🗑️ 刪除", key=f"del_{row['id']}"):
                    st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                    app.save_data(); st.rerun()
