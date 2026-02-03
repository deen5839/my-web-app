import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date
import io  # 確保導入此模組，修復 NameError

# 1. 網頁初始設定
st.set_page_config(
    page_title="個人理財數據帳本", 
    page_icon="💰", 
    layout="wide"
)

# 2. 強力 CSS 注入 (讓介面變漂亮，且隱藏多餘 UI)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stMetric {
        background-color: #ffffff !important;
        padding: 20px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
    }
    .stApp {
        background-color: #f0f2f6 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. 資料處理核心
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

# 4. 網頁 UI
st.title("💰 個人理財：數據記錄帳本")
st.info("助教小提醒：若切換收入/支出，分類選單會自動重置以確保數據安全。")

tab1, tab2 = st.tabs(["➕ 記帳與修正", "📊 數據清單與分析"])

with tab1:
    edit_data = None
    if st.session_state.editing_id is not None:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"正在編輯 ID #{st.session_state.editing_id}")

    # --- 輸入表單區 ---
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            # 日期
            default_date = date.today()
            if edit_data:
                default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
            r_date = st.date_input("選擇日期", default_date)
            
            # 收支類型
            r_type_list = ["支出", "收入"]
            r_type_idx = 0
            if edit_data and edit_data['type'] == "收入": r_type_idx = 1
            r_type = st.radio("收支類型", r_type_list, index=r_type_idx, horizontal=True)
            
            # 金額
            default_amount = 0.0
            if edit_data: default_amount = float(edit_data['amount'])
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=100.0, value=default_amount)
        
        with col2:
            # 定義分類
            if r_type == '收入':
                categories = ['薪水', '獎金', '投資', '其他']
            else:
                categories = ['飲食', '交通', '購物', '娛樂', '醫療', '其他']
            
            # 【終極修復】使用 key=r_type 強制重新渲染 widget
            # 這樣當 r_type 改變時，selectbox 會被當成一個全新的元件處理
            cat_idx = 0
            if edit_data and edit_data['category'] in categories:
                cat_idx = categories.index(edit_data['category'])
            
            category = st.selectbox(
                "分類標籤", 
                categories, 
                index=cat_idx, 
                key=f"cat_selector_{r_type}"
            )
            
            default_note = ""
            if edit_data: default_note = edit_data['note']
            note = st.text_input("備註內容", value=default_note)

        # 提交與放棄按鈕
        btn_col_a, btn_col_b = st.columns(2)
        submit_label = "🚀 更新紀錄" if st.session_state.editing_id else "🚀 存入載體"
        
        if btn_col_a.button(submit_label, use_container_width=True, type="primary"):
            if amount > 0:
                app.add_or_update_record(r_date, r_type, amount, category, note)
                st.success("數據處理成功！")
                st.rerun()
            else:
                st.error("金額不可為零。")
                
        if st.session_state.editing_id is not None:
            if btn_col_b.button("❌ 取消編輯", use_container_width=True):
                st.session_state.editing_id = None
                st.rerun()

# --- Tab 2: 分析與明細 ---
with tab2:
    if st.session_state.records:
        df = pd.DataFrame(st.session_state.records)
        df['amount'] = df['amount'].astype(float)
        
        income = df[df['type'] == '收入']['amount'].sum()
        expense = df[df['type'] == '支出']['amount'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("總收入", f"${income:,.0f}")
        c2.metric("總支出", f"${expense:,.0f}")
        c3.metric("淨資產", f"${income - expense:,.0f}")
        
        st.divider()
        
        # 顯示歷史清單
        for index, row in df.sort_values(by=['date', 'id'], ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['type']} - {row['category']} | ${row['amount']:,.0f}"):
                st.write(f"備註：{row['note']}")
                ec1, ec2 = st.columns(2)
                if ec1.button("✏️ 修正", key=f"e_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if ec2.button("🗑️ 刪除", key=f"d_{row['id']}"):
                    app.delete_record(row['id'])
                    st.rerun()
    else:
        st.info("帳本內尚無紀錄。")

st.divider()
st.caption("AI 帳本穩定運作中 | 修正 Widget 索引連動問題 ✅")
# 初始化 Session State (用於存儲搜尋紀錄)
if 'search_history' not in st.session_state:
    st.session_state.search_history = []

if 'financial_data' not in st.session_state:
    # 預設一些模擬數據，你可以替換成你原本的資料邏輯
    st.session_state.financial_data = pd.DataFrame({
        '日期': ['2024-01-01', '2024-01-10', '2024-02-01'],
        '項目': ['台積電股息', '生活開銷', '輝達股票回報'],
        '金額': [5000, -2000, 15000]
    })

def main():
    st.set_page_config(page_title="理財帳本 - 增強版", layout="wide")
    
    st.title("🐍 Python 理財帳本：備份與紀錄功能")
    st.write(f"目前狀態：修復完成 | 檔案穩定運作中")

    # --- 側邊欄：搜尋紀錄 ---
    st.sidebar.header("🔍 搜尋紀錄")
    search_query = st.sidebar.text_input("搜尋項目內容...", key="search_input")
    
    if st.sidebar.button("執行搜尋"):
        if search_query:
            if search_query not in st.session_state.search_history:
                st.session_state.search_history.insert(0, search_query)
                st.session_state.search_history = st.session_state.search_history[:10]

    if st.session_state.search_history:
        st.sidebar.write("最近搜尋：")
        for h in st.session_state.search_history:
            st.sidebar.text(f"📌 {h}")

    # --- 主介面：數據顯示 ---
    st.subheader("📊 理財數據清單")
    
    df = st.session_state.financial_data
    if search_query:
        # 過濾包含關鍵字的資料
        filtered_df = df[df['項目'].str.contains(search_query, na=False)]
    else:
        filtered_df = df

    st.dataframe(filtered_df, use_container_width=True)

    st.divider()

    # --- 備份功能區 ---
    st.subheader("💾 數據備份與導出")
    
    # 修正後的備份邏輯
    try:
        # 使用 utf-8-sig 編碼以確保 Excel 打開中文不亂碼
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_data = csv_buffer.getvalue()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="立即下載備份檔案 (.csv)",
            data=csv_data,
            file_name=f"financial_backup_{timestamp}.csv",
            mime="text/csv",
        )
        st.success("備份檔案已就緒，隨時可以下載。")
    except Exception as e:
        st.error(f"備份產生失敗：{e}")

if __name__ == "__main__":
    main()
