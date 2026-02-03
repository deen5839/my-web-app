import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date
import io

# 1. 網頁初始設定
st.set_page_config(
    page_title="個人理財數據帳本", 
    page_icon="💰", 
    layout="wide"
)

# 2. 數據處理核心
class WebAccounting:
    def __init__(self):
        self.filename = 'accounting_data.json'
        if 'records' not in st.session_state:
            st.session_state.records = self.load_data()
        if 'editing_id' not in st.session_state:
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
            st.error(f"數據存入檔案失敗：{e}")

    def add_or_update_record(self, r_date, r_type, amount, category, note):
        if st.session_state.editing_id is not None:
            for r in st.session_state.records:
                if r['id'] == st.session_state.editing_id:
                    r['date'] = r_date.strftime('%Y-%m-%d')
                    r['type'] = r_type
                    r['amount'] = amount
                    r['category'] = category
                    r['note'] = note
                    break
            st.session_state.editing_id = None
        else:
            new_id = 1 if not st.session_state.records else max(r['id'] for r in st.session_state.records) + 1
            record = {
                'id': new_id,
                'date': r_date.strftime('%Y-%m-%d'),
                'type': r_type,
                'amount': amount,
                'category': category,
                'note': note
            }
            st.session_state.records.append(record)
        self.save_data()

    def delete_record(self, r_id):
        st.session_state.records = [r for r in st.session_state.records if r['id'] != r_id]
        self.save_data()

app = WebAccounting()

# 3. 穩定搜尋與同步邏輯
search_query = st.query_params.get("q", "")

# 4. 側邊欄：搜尋與 Excel 導出
with st.sidebar:
    st.header("🔍 數據搜尋")
    def update_search():
        st.query_params["q"] = st.session_state.search_input

    new_q = st.text_input(
        "關鍵字搜尋", 
        value=search_query,
        key="search_input",
        on_change=update_search,
        placeholder="例如：午餐"
    )
    
    st.divider()
    st.header("💾 備份與導出")
    
    # 處理導出 Excel 的邏輯
    if st.session_state.records:
        export_df = pd.DataFrame(st.session_state.records)
        # 重新排序欄位方便閱讀
        export_df = export_df[['date', 'type', 'category', 'amount', 'note']]
        export_df.columns = ['日期', '類型', '分類', '金額', '備註']
        
        # 使用 BytesIO 建立 Excel 緩衝區，避免亂碼
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='理財紀錄')
            # 這裡可以自動調整欄寬
            worksheet = writer.sheets['理財紀錄']
            for i, col in enumerate(export_df.columns):
                column_len = max(export_df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, column_len)
        
        st.download_button(
            label="📥 下載 Excel 備份 (不亂碼版)",
            data=buffer.getvalue(),
            file_name=f"理財帳本備份_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.info("目前尚無數據可備份")

# 5. 網頁 UI 主介面
st.title("💰 個人理財：數據記錄帳本")

tab1, tab2, tab3 = st.tabs(["➕ 記帳與修正", "📊 數據分析", "📋 歷史清單"])

# 獲取數據
df = pd.DataFrame(st.session_state.records)
if not df.empty:
    df['amount'] = df['amount'].astype(float)
    if new_q:
        df = df[
            df['note'].str.contains(new_q, na=False, case=False) | 
            df['category'].str.contains(new_q, na=False, case=False) |
            df['type'].str.contains(new_q, na=False, case=False)
        ]

# --- Tab 1: 記帳 ---
with tab1:
    edit_data = None
    if st.session_state.editing_id is not None:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"正在編輯 ID #{st.session_state.editing_id}")

    col1, col2 = st.columns(2)
    with col1:
        default_date = date.today()
        if edit_data:
            default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
        r_date = st.date_input("選擇日期", default_date)
        r_type = st.radio("收支類型", ["支出", "收入"], index=0 if not edit_data or edit_data['type']=="支出" else 1, horizontal=True)
        
    with col2:
        amount = st.number_input("金額 (TWD)", min_value=0.0, step=10.0, value=float(edit_data['amount']) if edit_data else 0.0)
        categories = ['薪水', '獎金', '投資', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '娛樂', '醫療', '其他']
        cat_idx = 0
        if edit_data and edit_data['category'] in categories:
            cat_idx = categories.index(edit_data['category'])
        category = st.selectbox("分類標籤", categories, index=cat_idx)

    note = st.text_input("備註內容", value=edit_data['note'] if edit_data else "")

    if st.button("🚀 儲存紀錄", type="primary", use_container_width=True):
        if amount > 0:
            app.add_or_update_record(r_date, r_type, amount, category, note)
            st.success("數據儲存成功！")
            st.rerun()

# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        income = df[df['type'] == '收入']['amount'].sum()
        expense = df[df['type'] == '支出']['amount'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("搜尋結果收入", f"${income:,.0f}")
        c2.metric("搜尋結果支出", f"${expense:,.0f}")
        c3.metric("餘額", f"${income - expense:,.0f}")
        
        st.subheader("分類佔比")
        st.bar_chart(df.groupby('category')['amount'].sum())
    else:
        st.info("沒有數據可顯示。")

# --- Tab 3: 歷史清單 ---
with tab3:
    if not df.empty:
        for index, row in df.sort_values(by=['date'], ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"備註: {row['note']}")
                ec1, ec2 = st.columns(2)
                if ec1.button("✏️ 編輯", key=f"e_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if ec2.button("🗑️ 刪除", key=f"d_{row['id']}"):
                    app.delete_record(row['id'])
                    st.rerun()
    else:
        st.warning("清單為空。")
