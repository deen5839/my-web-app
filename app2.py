import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date

# 1. 網頁初始設定
st.set_page_config(
    page_title="理財數據帳本 Pro", 
    page_icon="💰", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 修正後的 CSS (參數名稱正確版)
st.markdown("""
    <style>
    /* 強化手機版顯示與滑動穩定性 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0px 0px;
        padding: 5px 15px;
    }
    /* 避免圖表區塊高度塌陷導致滑動亂跑 */
    .chart-box {
        min-height: 350px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 數據核心邏輯
class WebAccounting:
    def __init__(self):
        self.filename = 'accounting_data.json'
        if 'records' not in st.session_state:
            self.records = self.load_data()
            st.session_state.records = self.records
        else:
            self.records = st.session_state.records

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
            st.error(f"儲存失敗：{e}")

    def add_record(self, r_date, r_type, amount, category, note):
        new_id = 1 if not st.session_state.records else max(r['id'] for r in st.session_state.records) + 1
        new_data = {
            'id': new_id,
            'date': r_date.strftime('%Y-%m-%d'),
            'type': r_type,
            'amount': float(amount),
            'category': category,
            'note': note
        }
        st.session_state.records.append(new_data)
        self.save_data()

    def delete_record(self, r_id):
        st.session_state.records = [r for r in st.session_state.records if r['id'] != r_id]
        self.save_data()

app = WebAccounting()

# 3. 標題與數據整理
st.title("💰 理財數據帳本 Pro")

df = pd.DataFrame(st.session_state.records)
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'])
    df['date'] = pd.to_datetime(df['date'])
    
    # 頂部統計指標
    t_income = df[df['type'] == '收入']['amount'].sum()
    t_expense = df[df['type'] == '支出']['amount'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("總收入", f"${t_income:,.0f}")
    col2.metric("總支出", f"${t_expense:,.0f}", delta=f"-{t_expense:,.0f}", delta_color="inverse")
    col3.metric("結餘", f"${t_income - t_expense:,.0f}")

st.divider()

# 4. 功能分頁
tab1, tab2, tab3 = st.tabs(["➕ 記帳", "📊 分析", "📋 明細"])

with tab1:
    # 使用 clear_on_submit 確保儲存後「歸零」
    with st.form("my_form", clear_on_submit=True):
        st.subheader("新增收支紀錄")
        c1, c2 = st.columns(2)
        with c1:
            r_date = st.date_input("日期", date.today())
            r_type = st.radio("類型", ["支出", "收入"], horizontal=True)
        with c2:
            amount = st.number_input("金額", min_value=0.0, step=100.0)
            cats = ['薪水', '獎金', '投資', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '娛樂', '醫療', '住房', '其他']
            category = st.selectbox("分類", cats)
        
        note = st.text_input("備註")
        submitted = st.form_submit_button("✅ 儲存並歸零", use_container_width=True)
        
        if submitted:
            if amount > 0:
                app.add_record(r_date, r_type, amount, category, note)
                st.success("數據已存入帳本！")
                st.rerun()
            else:
                st.warning("請輸入有效金額")

with tab2:
    if not df.empty:
        st.subheader("支出分類佔比")
        exp_df = df[df['type'] == '支出']
        if not exp_df.empty:
            # 簡化統計邏輯，避免畫面亂跑
            pie_data = exp_df.groupby('category')['amount'].sum()
            # 使用橫向條形圖在手機上更穩定
            st.bar_chart(pie_data, horizontal=True)
        else:
            st.info("尚無支出紀錄")
            
        st.divider()
        st.subheader("收支趨勢")
        trend = df.pivot_table(index='date', columns='type', values='amount', aggfunc='sum').fillna(0)
        st.line_chart(trend)
    else:
        st.info("暫無數據")

with tab3:
    if not df.empty:
        # 簡單的搜尋功能
        search = st.text_input("🔍 搜尋備註...")
        view_df = df.copy()
        if search:
            view_df = view_df[view_df['note'].str.contains(search, na=False)]
        
        # 倒序顯示最新明細
        view_df = view_df.sort_values('date', ascending=False)
        for _, row in view_df.iterrows():
            with st.expander(f"{row['date'].strftime('%Y-%m-%d')} | {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"類型：{row['type']}")
                st.write(f"備註：{row['note']}")
                if st.button("刪除此筆", key=f"del_{row['id']}"):
                    app.delete_record(row['id'])
                    st.rerun()
    else:
        st.write("目前沒有紀錄")

st.markdown("---")
st.caption("我要精準理財，祝您天天快樂！")
