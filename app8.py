import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# --- 1. 網頁初始設定 ---
st.set_page_config(page_title="存股複利雪球 3.0", page_icon="🔥", layout="wide")

st.title("🔥 存股複利雪球 3.0 (高精準度台股歷史校正版)")
st.markdown("結合全球金融資料庫與台股歷史黃金校正庫，算給你聽！")

# --- 💡 內建台股特例「黃金歷史資料庫」(解決 yfinance 歷史缺漏問題) ---
STOCK_GOLDEN_DB = {
    "5706.TW": {2021: 0.30, 2022: 1.00, 2023: 0.30, 2024: 2.00, 2025: 2.75, 2026: 4.50}, # 鳳凰
    "1218.TW": {2021: 0.60, 2022: 1.00, 2023: 0.56, 2024: 0.00, 2025: 1.00, 2026: 1.32}, # 泰山
    "2330.TW": {2021: 10.25, 2022: 11.00, 2023: 11.75, 2024: 14.00, 2025: 16.50, 2026: 19.00}, # 台積電
}

# --- 2. 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    ticker = st.text_input("股票代號 (台股請加 .TW)", value="5706.TW").strip().upper()
    stock_sheets = st.number_input("持有張數 (1張=1000股)", value=10, min_value=1, step=1)
    
    start_year = st.number_input("歷史回測起始年份", value=2021, min_value=2000, max_value=2030, step=1)
    years_to_calc = st.slider("想要計算幾年？(最長20年)", min_value=1, max_value=20, value=6)
    
    st.divider()
    st.subheader("🛠️ 2026 最新股息手動微調")
    enable_manual_2026 = st.checkbox("手動指定 2026 年配息金額", value=False)
    manual_2026_div = st.number_input("2026年每股配息 (元)", value=4.50, step=0.01, format="%.2f")

total_shares = stock_sheets * 1000
current_year = 2026

# --- 3. 核心 API + 雙來源資料融合邏輯 ---
with st.spinner(f"📡 正在為您融合 {ticker} 的歷史真實數據與未來推算..."):
    try:
        # 建立完整的目標年份序列
        end_year = start_year + years_to_calc - 1
        full_years = pd.DataFrame({'Year': list(range(start_year, end_year + 1))})
        
        # 步驟 A: 嘗試從 yfinance 撈取原始數據
        stock = yf.Ticker(ticker)
        div_data = stock.dividends
        
        if not div_data.empty:
            df_div = pd.DataFrame(div_data).reset_index()
            df_div['Date'] = pd.to_datetime(df_div['Date'], utc=True).dt.tz_convert('Asia/Taipei')
            df_div['Year'] = df_div['Date'].dt.year
            yearly_div_raw = df_div.groupby('Year')['Dividends'].sum().reset_index()
        else:
            yearly_div_raw = pd.DataFrame(columns=['Year', 'Dividends'])
            
        # 合併時間軸
        yearly_div = pd.merge(full_years, yearly_div_raw, on='Year', how='left').fillna(0)
        
        # 步驟 B: 如果該股票在「黃金歷史資料庫」有備份，優先覆蓋 2025 (含) 以前的歷史資料
        if ticker in STOCK_GOLDEN_DB:
            golden_data = STOCK_GOLDEN_DB[ticker]
            for yr, val in golden_data.items():
                if yr in yearly_div['Year'].values:
                    yearly_div.loc[yearly_div['Year'] == yr, 'Dividends'] = val
                    
        # 步驟 C: 2026 年（當前年份）處理邏輯
        if enable_manual_2026:
            yearly_div.loc[yearly_div['Year'] == current_year, 'Dividends'] = manual_2026_div
        else:
            # 安全檢查：若 2026 年為 0 或沒有資料，自動帶入手動校正值
            mask_2026 = yearly_div['Year'] == current_year
            if mask_2026.any():
                val_2026 = yearly_div.loc[mask_2026, 'Dividends'].values[0]
                if val_2026 == 0:
                    yearly_div.loc[mask_2026, 'Dividends'] = manual_2026_div

        # 步驟 D: 未來年份 (> 2026) 安全延伸推算
        # 💡 安全防禦：先試著拿 2026 年的值，拿不到就拿 manual_2026_div，絕不讓陣列越界崩潰
        val_2026_list = yearly_div.loc[yearly_div['Year'] == current_year, 'Dividends'].values
        if len(val_2026_list) > 0 and val_2026_list[0] > 0:
            latest_div = val_2026_list[0]
        else:
            latest_div = manual_2026_div

        future_mask = yearly_div['Year'] > current_year
        yearly_div.loc[future_mask, 'Dividends'] = latest_div

        # 計算金額與累計
        yearly_div['当年領取總額'] = yearly_div['Dividends'] * total_shares
        yearly_div['累計已領股息'] = yearly_div['当年領取總額'].cumsum()
        
        # --- 4. 主畫面顯示 (UI 版面) ---
        st.subheader(f"🎯 {ticker} - 涵蓋 {start_year} 至 {end_year} 年（共 {len(yearly_div)} 年）股息累計")
        
        final_cumulative = yearly_div['累計已領股息'].iloc[-1]
        avg_yearly = yearly_div['当年領取總額'].mean()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("持有總股數", f"{total_shares:,} 股")
        c2.metric(f"這 {len(yearly_div)} 年累計總共領取", f"${final_cumulative:,.0f} 元")
        c3.metric("平均每年領取股息", f"${avg_yearly:,.0f} 元")
        
        st.divider()
        
        # 畫出圖表
        st.subheader("📊 現金股利逐年累計軌跡")
        g1, g2 = st.columns(2)
        
        with g1:
            fig_line = px.line(
                yearly_div, x="Year", y="累計已領股息", markers=True,
                title="💰 累計現金股利滾動圖 (逐年真實疊加)"
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
            
        # 詳細表格顯示
        with st.expander("📝 查看每年真實發放與累計明細"):
            display_df = yearly_div.copy()
            display_df['每股配發(元)'] = display_df['Dividends'].round(2)
            display_df['当年領取總額'] = display_df['当年領取總額'].astype(int)
            display_df['累計已領股息'] = display_df['累計已領股息'].astype(int)
            
            display_df.index = range(1, len(display_df) + 1)
            st.dataframe(display_df[['Year', '每股配發(元)', '当年領取總額', '累計已領股息']], use_container_width=True)

    except Exception as e:
        st.error(f"發生錯誤：{e}")
