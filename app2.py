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
            except: return []
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
                        'type': r_type,
                        'amount': amount,
                        'category': category,
                        'note': note
                    })
                    break
            st.session_state.editing_id = None
        else:
            new_id = 1 if not st.session_state.records else max(r['id'] for r in st.session_state.records) + 1
            st.session_state.records.append({
                'id': new_id,
                'date': r_date.strftime('%Y-%m-%d'),
                'type': r_type,
                'amount': amount,
                'category': category,
                'note': note
            })
        self.save_data()

if 'app' not in st.session_state:
    st.session_state.app = WebAccounting()
app = st.session_state.app

# 3. 側邊欄：搜尋與 Excel 備份
with st.sidebar:
    st.header("🔍 數據管理")
    search_query = st.text_input("關鍵字搜尋", placeholder="搜尋備註或分類...", key="sidebar_search")
    
    st.divider()
    st.header("📊 檔案導出")
    
    if st.session_state.records:
        export_df = pd.DataFrame(st.session_state.records)
        export_df = export_df[['date', 'type', 'category', 'amount', 'note']]
        export_df.columns = ['日期', '收支類型', '分類', '金額', '備註']
        
        # 改用 openpyxl 引擎，這是最通用的 Excel 引擎
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
            st.error("Excel 產生失敗，請確認是否安裝 openpyxl")
    else:
        st.info("尚無數據可導出")

# 4. 數據預處理
df = pd.DataFrame(st.session_state.records)
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    if search_query:
        df = df[
            df['note'].str.contains(search_query, na=False, case=False) | 
            df['category'].str.contains(search_query, na=False, case=False)
        ]

# 5. UI 主介面
# --- 啟動歡迎詞 ---
now_hour = datetime.now().hour
if now_hour < 12:
    greeting = "🌅 早上好！今天也是充滿數據力的一天。"
elif now_hour < 18:
    greeting = "☀️ 下午好！來對個帳，讓理財更有 Vibe。"
else:
    greeting = "🌙 晚上好！辛苦了，整理一下今天的收支吧。"

st.toast(f"系統已就緒：{greeting}") # 右下角會跳出小通知
st.markdown(f"### {greeting}") 
st.caption("🚀 歡迎使用 **個人理財數據載體 v1.1** | 讓你的每一分錢都有跡可循")
st.divider()

st.title("💰 個人理財：數據記錄帳本")
tab1, tab2, tab3 = st.tabs(["➕ 記帳與修正", "📊 數據分析", "📋 歷史清單"])


# --- Tab 1: 記帳 (已加入私密加密功能) ---
with tab1:
    edit_data = None
    if st.session_state.editing_id:
        edit_data = next((r for r in st.session_state.records if r['id'] == st.session_state.editing_id), None)
        st.warning(f"🔧 正在編輯模式...")

    r_type = st.radio("收支類型", ["支出", "收入"], index=0 if not edit_data or edit_data['type'] == "支出" else 1, horizontal=True)

    with st.form("input_form", clear_on_submit=(st.session_state.editing_id is None)):
        col1, col2 = st.columns(2)
        with col1:
            default_date = date.today()
            if edit_data:
                # 這裡加個防錯，確保日期格式正確
                try:
                    default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
                except:
                    default_date = date.today()
            r_date = st.date_input("日期", default_date)
            
        with col2:
            amount = st.number_input("金額 (TWD)", min_value=0.0, step=10.0, value=float(edit_data['amount']) if edit_data else 0.0)
            # 增加「軟體訂閱」分類
            categories = ['薪水', '獎金', '投資', '洗衣店營收', '其他'] if r_type == '收入' else ['飲食', '交通', '購物', '娛樂', '醫療', '軟體訂閱', '其他']
            
            cat_idx = 0
            if edit_data and edit_data['category'] in categories:
                cat_idx = categories.index(edit_data['category'])
            category = st.selectbox("分類標籤", categories, index=cat_idx)

        # 備註輸入
        note = st.text_input("備註內容", value=edit_data['note'].replace("[私密] ", "") if edit_data else "", placeholder="例如：Steam 遊戲...")
        
        # --- 這裡就是新加入的隱藏功能 ---
        is_secret = st.checkbox("🤫 開啟私密模式 (在清單中隱藏具體備註內容)")
        # ----------------------------

        submit_btn = st.form_submit_button("🚀 儲存紀錄", use_container_width=True)
        
        if submit_btn:
            if amount > 0:
                # 如果勾選私密，就在存檔時加上標記
                final_note = f"[私密] {note}" if is_secret else note
                app.add_or_update_record(r_date, r_type, amount, category, final_note)
                st.success("數據已安全存檔！")
                st.rerun()
# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        inc = df[df['type'] == '收入']['amount'].sum()
        exp = df[df['type'] == '支出']['amount'].sum()
        c1.metric("搜尋結果收入", f"${inc:,.0f}")
        c2.metric("搜尋結果支出", f"${exp:,.0f}")
        c3.metric("餘額", f"${inc-exp:,.0f}")
        
        st.divider()
        st.subheader("📌 支出佔比分析")
        exp_data = df[df['type'] == '支出'].groupby('category')['amount'].sum()
        if not exp_data.empty:
            st.bar_chart(exp_data, use_container_width=True)
    else:
        st.info("沒有數據。")

# --- Tab 3: 歷史清單 (優化版) ---
with tab3:
    if not df.empty:
        # 解決清單過長：增加月份篩選器
        df['date_dt'] = pd.to_datetime(df['date'])
        available_months = df['date_dt'].dt.strftime('%Y-%m').unique().tolist()
        available_months.sort(reverse=True)
        
        col_filter1, col_filter2 = st.columns([1, 2])
        with col_filter1:
            selected_month = st.selectbox("📅 選擇月份", ["顯示全部"] + available_months)
        
        # 根據選擇過濾數據
        display_df = df.copy()
        if selected_month != "顯示全部":
            display_df = display_df[display_df['date_dt'].dt.strftime('%Y-%m') == selected_month]

        if st.session_state.editing_id:
            if st.button("❌ 放棄修改"):
                st.session_state.editing_id = None
                st.rerun()

        # 這裡改用過濾後的 display_df
        for _, row in display_df.sort_values(by=['date', 'id'], ascending=False).iterrows():
            # ... (後面的 expander 顯示邏輯不變)
            with st.expander(f"📅 {row['date']} | {row['type']} - {row['category']} | ${row['amount']:,.0f}"):
                # 在 Tab 3 歷史清單循環中修改：
                raw_note = row['note'] if row['note'] else '無'
                # 如果備註開頭是 [私密]，我們就只顯示鎖頭，不顯示內容
                display_note = "🔒 內容已加密 (私密項目)" if raw_note.startswith("[私密]") else raw_note
                st.write(f"📝 備註: {display_note}")
                ec1, ec2 = st.columns(2)
                if ec1.button("✏️ 編輯", key=f"edit_btn_{row['id']}"):
                    st.session_state.editing_id = row['id']
                    st.rerun()
                if ec2.button("🗑️ 刪除", key=f"del_btn_{row['id']}"):
                    st.session_state.records = [r for r in st.session_state.records if r['id'] != row['id']]
                    app.save_data()
                    st.rerun()
