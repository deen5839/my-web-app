import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
import os

# --- 1. 網頁初始設定 ---
st.set_page_config(page_title="存股複利雪球 3.1", page_icon="🔥", layout="wide")

st.title("🔥 存股複利雪球 3.1 (動態外部校正 + API 優先版)")
st.markdown("連線全球 API，並自動結合外部校正資料庫，數據精準不硬寫！")

# --- 💡 讀取外部 CSV 校正檔 (若無檔案則建立空結構，方便擴充) ---
CSV_FILE = "custom_dividends.csv"
if os.path.exists(CSV_FILE):
    try:
        custom_db = pd.read_csv(CSV_FILE)
    except Exception:
        custom_db = pd.DataFrame(columns=['Ticker', 'Year', 'Dividend'])
else:
    # 範例數據：可隨時抽離改存成 custom_dividends.csv 檔案
    custom_db = pd.DataFrame([
        {'Ticker': '5706.TW', 'Year': 2021, 'Dividend': 0.30},
        {'Ticker': '5706.TW', 'Year': 2022, 'Dividend': 1.00},
        {'Ticker': '5706.TW', 'Year': 2023, 'Dividend': 0.30},
        {'Ticker': '5706.TW', 'Year': 2024, 'Dividend': 2.00},
        {'Ticker': '5706.TW', 'Year': 2025, 'Dividend': 2.75},
        {'Ticker': '1218.TW', 'Year': 2024, 'Dividend': 0.00},
    ])

# --- 2. 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    ticker = st.text_input("股票代號 (台股請加 .TW)", value="5706.TW").strip().upper()
    stock_sheets = st.number_input("持有張數 (1張=1000股)", value=None, min_value=1, step=1)
    
    start_year = st.number_input("歷史回測起始年份", value=2026, min_value=2000, max_value=2030, step=1)
    years_to_calc = st.slider("想要計算幾年？(最長20年)", min_value=1, max_value=20, value=1)
    
    st.divider()
    st.subheader("🛠️ 2026 特例手動強制覆蓋")
    force_manual_2026 = st.checkbox("強制指定 2026 年配息金額", value=False)
    manual_2026_div = st.number_input("2026年每股配息 (元)", value=4.54, step=0.01, format="%.2f")

total_shares = stock_sheets * 1000
current_year = 2026

# --- 3. 核心 API + 自動校正融合邏輯 ---
with st.spinner(f"📡 正在為您連線 API 並處理 {ticker} 數據..."):
    try:
        end_year = start_year + years_to_calc - 1
        full_years = pd.DataFrame({'Year': list(range(start_year, end_year + 1))})
        
        # 步驟 A: 抓取 yfinance 數據
        stock = yf.Ticker(ticker)
        div_data = stock.dividends
        
        if not div_data.empty:
            df_div = pd.DataFrame(div_data).reset_index()
            df_div['Date'] = pd.to_datetime(df_div['Date'], utc=True).dt.tz_convert('Asia/Taipei')
            df_div['Year'] = df_div['Date'].dt.year
            yearly_div_raw = df_div.groupby('Year')['Dividends'].sum().reset_index()
        else:
            yearly_div_raw = pd.DataFrame(columns=['Year', 'Dividends'])
            
        yearly_div = pd.merge(full_years, yearly_div_raw, on='Year', how='left').fillna(0)
        
        # 步驟 B: 從外部表格校正庫 (custom_db) 自動覆蓋已知誤植的歷史年份
        ticker_custom = custom_db[custom_db['Ticker'] == ticker]
        if not ticker_custom.empty:
            for _, row in ticker_custom.iterrows():
                yr = int(row['Year'])
                val = float(row['Dividend'])
                if yr in yearly_div['Year'].values and yr < current_year:
                    yearly_div.loc[yearly_div['Year'] == yr, 'Dividends'] = val

        # 步驟 C: 2026 年配息判定 (API 優先)
        if force_manual_2026:
            yearly_div.loc[yearly_div['Year'] == current_year, 'Dividends'] = manual_2026_div
        else:
            # 優先拿 API 抓到的真實金額 (例如鳳凰的 4.54)
            api_2026 = yearly_div.loc[yearly_div['Year'] == current_year, 'Dividends'].values
            if len(api_2026) == 0 or api_2026[0] == 0:
                # 沒抓到才給預設值
                yearly_div.loc[yearly_div['Year'] == current_year, 'Dividends'] = manual_2026_div

        # 步驟 D: 未來年份 (> 2026) 安全延伸
        val_2026_list = yearly_div.loc[yearly_div['Year'] == current_year, 'Dividends'].values
        latest_div = val_2026_list[0] if len(val_2026_list) > 0 and val_2026_list[0] > 0 else manual_2026_div

        future_mask = yearly_div['Year'] > current_year
        yearly_div.loc[future_mask, 'Dividends'] = latest_div

        # 計算金額與累計
        yearly_div['当年領取總額'] = yearly_div['Dividends'] * total_shares
        yearly_div['累計已領股息'] = yearly_div['当年領取總額'].cumsum()
        
        # --- 4. 主畫面顯示 ---
        st.subheader(f"🎯 {ticker} - 涵蓋 {start_year} 至 {end_year} 年股息累計")
        
        final_cumulative = yearly_div['累計已領股息'].iloc[-1]
        avg_yearly = yearly_div['当年領取總額'].mean()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("持有總股數", f"{total_shares:,} 股")
        c2.metric(f"這 {len(yearly_div)} 年累計總共領取", f"${final_cumulative:,.0f} 元")
        c3.metric("平均每年領取股息", f"${avg_yearly:,.0f} 元")
        
        st.divider()
        
        g1, g2 = st.columns(2)
        with g1:
            fig_line = px.line(
                yearly_div, x="Year", y="累計已領股息", markers=True,
                title="💰 累計現金股利滾動圖"
            )
            fig_line.update_traces(line=dict(color="#FFC107", width=4), marker=dict(size=10, color="#FF5722"))
            st.plotly_chart(fig_line, use_container_width=True)
            
        with g2:
            fig_bar = px.bar(
                yearly_div, x="Year", y="当年領取總額",
                title="💵 每年實際配發總股息",
                color_discrete_sequence=['#1E88E5']
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with st.expander("📝 查看每年真實發放與累計明細"):
            display_df = yearly_div.copy()
            display_df['每股配發(元)'] = display_df['Dividends'].round(2)
            display_df['当年領取總額'] = display_df['当年領取總額'].astype(int)
            display_df['累計已領股息'] = display_df['累計已領股息'].astype(int)
            display_df.index = range(1, len(display_df) + 1)
            st.dataframe(display_df[['Year', '每股配發(元)', '当年領取總額', '累計已領股息']], use_container_width=True)

    except Exception as e:
        st.error(f"發生錯誤：{e}")
