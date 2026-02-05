import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date, timedelta
import io
import uuid
import plotly.express as px

# ==========================================
# 1. 網頁初始設定
# ==========================================
st.set_page_config(
    page_title="個人理財數據帳本", 
    page_icon="💰", 
    layout="wide"
)

# ==========================================
# 2. 數據處理核心類別
# ==========================================
class WebAccounting:
    def __init__(self):
        # 確保資料儲存容器存在於 Session State
        if 'records' not in st.session_state:
            st.session_state.records = []
        
        # 確保編輯 ID 追蹤存在
        if 'editing_id' not in st.session_state:
            st.session_state.editing_id = None

    def save_notice(self):
        """顯示存檔成功提示"""
        st.toast("✅ 數據已寫入載體，請點擊左側下載備份！", icon="💾")
        return True

    def add_or_update_record(self, r_date, r_type, amount, category, note):
        """處理新增與修改邏輯"""
        if st.session_state.editing_id is not None:
            # --- 修改既有資料 ---
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
            # --- 新增全新資料 ---
            new_id = str(uuid.uuid4())[:8]
            st.session_state.records.append({
                'id': new_id, 
                'date': r_date.strftime('%Y-%m-%d'),
                'type': r_type, 
                'amount': amount, 
                'category': category, 
                'note': note
            })
        
        # 執行提示
        self.save_notice()

# --- 初始化應用執行個體 ---
if 'app' not in st.session_state:
    st.session_state.app = WebAccounting()

app = st.session_state.app

# ==========================================
# 3. 側邊欄：搜尋、備份與還原功能
# ==========================================
with st.sidebar:
    st.header("🔍 數據管理系統")
    search_query = st.text_input("搜尋備註關鍵字...", placeholder="例如：晚餐")
    
    st.divider()
    
    st.header("📤 資料還原")
    st.write("重新整理網頁後，請上傳 JSON 檔恢復數據：")
    uploaded_file = st.file_uploader("選擇備份檔案", type="json")
    
    if uploaded_file is not None:
        try:
            st.session_state.records = json.load(uploaded_file)
            st.success("✅ 資料已成功還原！")
        except Exception as e:
            st.error(f"❌ 檔案讀取失敗: {e}")

    st.divider()
    
    st.header("📥 備份與導出")
    if st.session_state.records:
        # JSON 備份 (供系統還原使用)
        json_data = json.dumps(st.session_state.records, ensure_ascii=False, indent=4)
        st.download_button(
            label="💾 下載 JSON 備份 (防消失)",
            data=json_data,
            file_name=f"理財備份_{date.today()}.json",
            mime="application/json",
            use_container_width=True
        )
        
        # Excel 導出 (供報表查看使用)
        df_export = pd.DataFrame(st.session_state.records)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False)
        
        st.download_button(
            label="📊 導出 Excel 報表",
            data=buffer.getvalue(),
            file_name=f"財務月報_{date.today()}.xlsx",
            use_container_width=True
        )
    else:
        st.info("尚無數據可下載備份")

# ==========================================
# 4. 數據預處理 (過濾搜尋內容)
# ==========================================
df = pd.DataFrame(st.session_state.records)
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    if search_query:
        # 執行備註內容搜尋
        df = df[df['note'].str.contains(search_query, na=False, case=False)]

# ==========================================
# 5. UI 主介面與招呼語
# ==========================================
st.title("💰 個人理財數據載體")

# 校正台灣時間 (UTC+8)
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

# 設定分頁功能
tab1, tab2, tab3 = st.tabs(["➕ 數據記帳", "📊 數據趨勢分析", "📋 歷史明細"])

# --- Tab 1: 數據輸入與修正 ---
with tab1:
    # 檢查是否處於編輯模式
    edit_item = None
    if st.session_state.editing_id:
        edit_item = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"🔧 正在修改數據 (ID: {st.session_state.editing_id})")

    # 收支類型切換
    r_type = st.radio("收支類型", ["支出", "收入"], index=0 if not edit_item or edit_item['type'] == "支出" else 1, horizontal=True)
    
    with st.form("input_form", clear_on_submit=(not st.session_state.editing_id)):
        col_a, col_b = st.columns(2)
        
        with col_a:
            # 日期選取
            d_val = datetime.strptime(edit_item['date'], '%Y-%m-%d').date() if edit_item else date.today()
            r_date = st.date_input("日期", d_val)
            
        with col_b:
            # 金額輸入
            amt_val = float(edit_item['amount']) if edit_item else 0.0
            r_amount = st.number_input("金額 (TWD)", min_value=0.0, step=10.0, value=amt_val)
            
            # 分類連動選單
            income_cats = ['薪水', '獎金', '投資', '其他']
            expense_cats = ['飲食', '交通', '購物', '醫療', '訂閱', '其他']
            current_cats = income_cats if r_type == '收入' else expense_cats
            
            # 修正分類對齊邏輯
            idx = 0
            if edit_item and edit_item['category'] in current_cats:
                idx = current_cats.index(edit_item['category'])
            
            r_category = st.selectbox("分類標籤", current_cats, index=idx)
            
        # 備註輸入
        r_note = st.text_input("備註說明", value=edit_item['note'] if edit_item else "")
        
        # 提交按鈕
        if st.form_submit_button("🚀 寫入本地載體", use_container_width=True):
            if r_amount > 0:
                app.add_or_update_record(r_date, r_type, r_amount, r_category, r_note)
                st.rerun()

# --- Tab 2: 數據分析 (包含收入長條圖與預算進度) ---
with tab2:
    if not df.empty:
        # 計算核心指標
        sum_in = df[df['type'] == '收入']['amount'].sum()
        sum_ex = df[df['type'] == '支出']['amount'].sum()
        
        st.subheader("💰 財務現況概覽")
        m1, m2, m3 = st.columns(3)
        m1.metric("總收入", f"${sum_in:,.0f}")
        m2.metric("總支出", f"${sum_ex:,.0f}", delta=f"-{sum_ex:,.0f}", delta_color="inverse")
        m3.metric("淨資產", f"${sum_in - sum_ex:,.0f}")
        
        st.divider()
        
        # 預算執行進度 (橫向長條與數據)
        st.subheader("🎯 本月預算執行進度")
        user_budget = st.number_input("💸 設定本月支出預算", min_value=1000, value=15000, step=500)
        pct = min(sum_ex / user_budget, 1.0)
        
        c_p, c_v = st.columns([4, 1])
        with c_p:
            st.progress(pct)
        with c_v:
            st.write(f"**{pct*100:.1f}%**")
        st.write(f"📊 執行狀況：**${sum_ex:,.0f}** / ${user_budget:,.0f}")
        
        st.divider()
        
        # 雙圖表展示
        c_l, c_r = st.columns(2)
        with c_l:
            # 收入來源長條圖
            in_data = df[df['type'] == '收入']
            if not in_data.empty:
                st.plotly_chart(px.bar(in_data.groupby('category')['amount'].sum().reset_index(), 
                                       x='category', y='amount', title="收入來源占比", color='category'), use_container_width=True)
            else:
                st.info("尚無收入數據可分析")
                
        with c_r:
            # 支出比例圓餅圖
            ex_data = df[df['type'] == '支出']
            if not ex_data.empty:
                st.plotly_chart(px.pie(ex_data.groupby('category')['amount'].sum().reset_index(), 
                                       values='amount', names='category', title="支出類別分布", hole=0.3), use_container_width=True)
            else:
                st.info("尚無支出數據可分析")
    else:
        st.info("📊 尚未有數據進行分析。")

# --- Tab 3: 歷史明細清單 ---
with tab3:
    if not df.empty:
        # 依日期降冪排列
        for _, row in df.sort_values(by='date', ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - ${row['amount']:,.0f}"):
                st.write(f"📝 備註: {row['note']}")
                ec1, ec2 = st.columns(2)
                
                if ec1.button("✏️ 修改數據", key=f"e_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                    
                if ec2.button("🗑️ 刪除紀錄", key=f"d_{row['id']}"):
                    st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                    st.toast("🗑️ 數據已刪除")
                    st.rerun()
    else:
        st.info("📋 尚無歷史紀錄。")

# ==========================================
# 程式結束 (本版本約 284 行規格，包含排版空行)
# ==========================================
