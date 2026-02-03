import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date

# 1. 網頁初始設定
st.set_page_config(
    page_title="理財數據帳本 Pro", 
    page_icon="💎", 
    layout="wide",
    initial_sidebar_state="collapsed" # 手機版預設縮起側邊欄，減少視覺干擾
)

# 穩定 UI 的 CSS
st.markdown("""
    <style>
    /* 防止圖表容器跳動 */
    .chart-container {
        min-height: 400px;
    }
    /* 優化手機點擊區域 */
    .stButton button {
        height: 3em;
        margin-top: 10px;
    }
    /* 強化卡片感 */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e6e9ef;
        padding: 15px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_content_label=True)

# 2. 數據處理核心
class WebAccounting:
    def __init__(self):
        self.filename = 'accounting_data.json'
        if 'records' not in st.session_state:
            st.session_state.records = self.load_data()
        
        # 初始化表單狀態鍵值，用於歸零
        if 'form_amount' not in st.session_state:
            self.reset_form_state()

    def reset_form_state(self):
        st.session_state.form_amount = 0.0
        st.session_state.form_note = ""
        st.session_state.form_category = "其他"
        st.session_state.editing_id = None

    def load_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_data(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(st.session_state.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"數據存入失敗：{e}")

    def add_or_update_record(self, r_date, r_type, amount, category, note):
        if st.session_state.editing_id is not None:
            for r in st.session_state.records:
                if r['id'] == st.session_state.editing_id:
                    r.update({
                        'date': r_date.strftime('%Y-%m-%d'),
                        'type': r_type, 'amount': amount,
                        'category': category, 'note': note
                    })
                    break
        else:
            new_id = 1 if not st.session_state.records else max(r['id'] for r in st.session_state.records) + 1
            st.session_state.records.append({
                'id': new_id, 'date': r_date.strftime('%Y-%m-%d'),
                'type': r_type, 'amount': amount,
                'category': category, 'note': note
            })
        self.save_data()
        self.reset_form_state() # 儲存後立即歸零

    def delete_record(self, r_id):
        st.session_state.records = [r for r in st.session_state.records if r['id'] != r_id]
        self.save_data()

app = WebAccounting()

# 3. 頂部導航與搜尋
search_query = st.query_params.get("q", "")

# 4. 主介面設計
st.title("💰 理財數據帳本 Pro")

# 數據計算
df = pd.DataFrame(st.session_state.records)
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'])
    df['date'] = pd.to_datetime(df['date'])
    
    # 搜尋過濾
    if search_query:
        df = df[df['note'].str.contains(search_query, na=False, case=False) | 
                df['category'].str.contains(search_query, na=False, case=False)]

    # 統計指標
    t_income = df[df['type'] == '收入']['amount'].sum()
    t_expense = df[df['type'] == '支出']['amount'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("總收入", f"${t_income:,.0f}")
    m2.metric("總支出", f"${t_expense:,.0f}", delta=f"-{t_expense:,.0f}", delta_color="inverse")
    m3.metric("本期結餘", f"${t_income - t_expense:,.0f}")

st.divider()

# 分頁標籤
tab1, tab2, tab3 = st.tabs(["➕ 快速記帳", "📊 數據分析", "📋 歷史明細"])

# --- Tab 1: 記帳 (解決歸零問題) ---
with tab1:
    with st.form("accounting_form", clear_on_submit=True):
        st.subheader("新增紀錄")
        c1, c2 = st.columns(2)
        with c1:
            r_date = st.date_input("日期", date.today())
            r_type = st.radio("類型", ["支出", "收入"], horizontal=True)
        with c2:
            # 使用 form 內的元件，儲存後會自動重置 UI
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=100.0, key="input_amount")
            categories = ['薪水', '獎金', '投資', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '娛樂', '醫療', '住房', '其他']
            category = st.selectbox("分類", categories)
        
        note = st.text_input("備註 (例如：午餐、股票分紅)", key="input_note")
        
        submitted = st.form_submit_button("✅ 儲存數據", use_container_width=True)
        if submitted:
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.success("紀錄成功！欄位已重置。")
                st.rerun()
            else:
                st.error("請輸入大於 0 的金額")

# --- Tab 2: 分析 (解決佈局亂跑問題) ---
with tab2:
    if not df.empty:
        # 使用容器固定圖表，避免滑動時內容閃爍
        with st.container():
            st.subheader("支出分佈 (按類別)")
            exp_df = df[df['type'] == '支出']
            if not exp_df.empty:
                # 簡單穩定的圖表，適合手機閱讀
                chart_data = exp_df.groupby('category')['amount'].sum().sort_values(ascending=False)
                st.bar_chart(chart_data, color="#FF4B4B")
            else:
                st.info("尚無支出數據可供分析")
            
            st.divider()
            
            st.subheader("每日收支趨勢")
            trend_df = df.pivot_table(index='date', columns='type', values='amount', aggfunc='sum').fillna(0)
            st.line_chart(trend_df)
    else:
        st.info("尚未有數據，請先前往記帳。")

# --- Tab 3: 明細 ---
with tab3:
    if not df.empty:
        # 搜尋功能
        s_input = st.text_input("🔍 搜尋明細", value=search_query, placeholder="輸入關鍵字...")
        if s_input != search_query:
            st.query_params["q"] = s_input
            st.rerun()

        # 顯示明細表
        display_df = df.sort_values('date', ascending=False).copy()
        display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
        
        for idx, row in display_df.iterrows():
            with st.expander(f"{row['date']} | {row['type']} | {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"**備註：** {row['note'] if row['note'] else '無'}")
                if st.button("🗑️ 刪除", key=f"del_{row['id']}", use_container_width=True):
                    app.delete_record(row['id'])
                    st.rerun()
    else:
        st.write("清單空空如也。")

st.markdown("---")
st.caption("理財帳本穩定版 - 祝您心情愉快")
