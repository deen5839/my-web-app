import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# --- 1. 網頁初始設定 ---
st.set_page_config(page_title="存股複利雪球 2.0", page_icon="🔥", layout="wide")

st.title("🔥 存股複利雪球 2.0 (真實歷史平均 + 未來推算版)")
st.markdown("連線華爾街資料庫，用『真實歷史平均股息』為你預測未來的複利雪球！")

# --- 2. 側邊欄輸入設定 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    ticker = st.text_input("股票代號 (台股請加 .TW)", value="1218.TW")
    stock_sheets = st.number_input("持有張數 (1張=1000股)", value=226, min_value=1, step=1)
    start_year = st.number_input("買入年份", value=2026, min_value=1990, max_value=2030, step=1)
    projection_years = st.slider("想要預估未來幾年？", min_value=1, max_value=30, value=10)
    lookback_years = st.slider("參考過去幾年歷史配息算平均？", min_value=1, max_value=20, value=5)

total_shares = stock_sheets * 1000

# --- 3. 核心 API 串接與計算邏輯 ---
with st.spinner(f"📡 正在從全球金融資料庫撈取 {ticker} 的歷史配息..."):
    try:
        stock = yf.Ticker(ticker)
        div_data = stock.dividends
        
        if div_data.empty:
            st.warning(f"⚠️ 找不到 {ticker} 的配息資料，可能是代號錯誤，或 Yahoo 尚未收錄。")
        else:
            df_div = pd.DataFrame(div_data).reset_index()
            df_div['Date'] = pd.to_datetime(df_div['Date'], utc=True)
            df_div['Year'] = df_div['Date'].dt.year
            
            # 1. 抓取過往 N 年的歷史配息來計算「平均每股股息」
            current_year = datetime.now().year
            historical_df = df_div[(df_div['Year'] < current_year) & (df_div['Year'] >= current_year - lookback_years)]
            
            if historical_df.empty:
                # 備用方案：若抓不到歷史則取全記錄平均
                avg_div_per_share = df_div.groupby('Year')['Dividends'].sum().mean()
            else:
                avg_div_per_share = historical_df.groupby('Year')['Dividends'].sum().mean()
            
            # 2. 從 start_year (2026) 開始，建立未來的推算年份報表
            future_years = [start_year + i for i in range(projection_years)]
            yearly_div = pd.DataFrame({'Year': future_years})
            
            yearly_div['每股配發(元)'] = avg_div_per_share
            yearly_div['當年領取總額'] = avg_div_per_share * total_shares
            # 💡 這邊就會從 2026 年開始一年一年往下累加！
            yearly_div['累計已領股息'] = yearly_div['當年領取總額'].cumsum()
            
            # --- 4. 主畫面顯示 (UI 版面) ---
            st.subheader(f"🎯 {ticker} - 從 {start_year} 年起預估 {projection_years} 年領息雪球")
            
            final_cumulative = yearly_div['累計已領股息'].iloc[-1]
            avg_yearly = yearly_div['當年領取總額'].iloc[0]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("持有總股數", f"{total_shares:,} 股")
            c2.metric(f"預估 {projection_years} 年總共領", f"${final_cumulative:,.0f}")
            c3.metric("預估每年領取 (依歷史平均)", f"${avg_yearly:,.0f}")
            
            st.divider()
            
            # 圖表展示
            st.subheader("📊 未來複利雪球推估軌跡")
            g1, g2 = st.columns(2)
            
            with g1:
                fig_line = px.line(
                    yearly_div, x="Year", y="累計已領股息", markers=True,
                    title="💰 累計股息滾動圖 (從買入年一路疊加)"
                )
                fig_line.update_traces(line=dict(color="#FFC107", width=4), marker=dict(size=10, color="#FF5722"))
                st.plotly_chart(fig_line, use_container_width=True)
                
            with g2:
                fig_bar = px.bar(
                    yearly_div, x="Year", y="當年領取總額",
                    title="💵 每年預估入帳股息",
                    color_discrete_sequence=['#1E88E5']
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
            # 詳細表格
            with st.expander("📝 查看未來每年預估發放明細"):
                display_df = yearly_div.copy()
                display_df['每股配發(元)'] = display_df['每股配發(元)'].round(2)
                display_df['當年領取總額'] = display_df['當年領取總額'].astype(int)
                display_df['累計已領股息'] = display_df['累計已領股息'].astype(int)
                
                display_df.index = range(1, len(display_df) + 1)
                st.dataframe(display_df[['Year', '每股配發(元)', '當年領取總額', '累計已領股息']], use_container_width=True)

    except Exception as e:
        st.error(f"發生錯誤：{e}")
