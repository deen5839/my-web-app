import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# --- 1. 網頁初始設定 ---
st.set_page_config(page_title="存股複利雪球 2.0", page_icon="🔥", layout="wide")

st.title("🔥 存股複利雪球 2.0 (真實歷史回測版)")
st.markdown("直接連線華爾街資料庫，用『真實發放的股息』算給你聽！")

# --- 2. 側邊欄輸入設定 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    # 台股在 Yahoo Finance 的代號後面要加 .TW
    ticker = st.text_input("股票代號 (台股請加 .TW)", value="1218.TW")
    stock_sheets = st.number_input("持有張數 (1張=1000股)", value=226, min_value=1, step=1)
    lookback_years = st.slider("回測過去幾年？", min_value=1, max_value=20, value=10)

total_shares = stock_sheets * 1000

# --- 3. 核心 API 串接與計算邏輯 ---
# 加上讀取動畫，讓等待的時間變高級
with st.spinner(f"📡 正在從全球金融資料庫撈取 {ticker} 的歷史配息..."):
    try:
        # 召喚 yfinance 抓取股票資料
        stock = yf.Ticker(ticker)
        div_data = stock.dividends
        
        if div_data.empty:
            st.warning(f"⚠️ 找不到 {ticker} 的配息資料，可能是代號錯誤，或 Yahoo 尚未收錄。")
        else:
            # 將抓下來的資料轉換成 Pandas 報表
            df_div = pd.DataFrame(div_data).reset_index()
            # 將時間轉換成標準格式並萃取出「年份」
            df_div['Date'] = pd.to_datetime(df_div['Date'], utc=True)
            df_div['Year'] = df_div['Date'].dt.year
            
            # 過濾出你要的「過去 N 年」
            current_year = datetime.now().year
            start_year = current_year - lookback_years
            df_filtered = df_div[df_div['Year'] >= start_year].copy()
            
            # 💡 這裡用到了你最熟的「樞紐分析」邏輯：把同一個年份的股息加總
            yearly_div = df_filtered.groupby('Year')['Dividends'].sum().reset_index()
            
            # 算出這 226 張真實領到的錢
            yearly_div['當年領取總額'] = yearly_div['Dividends'] * total_shares
            yearly_div['累計已領股息'] = yearly_div['當年領取總額'].cumsum()
            
            # --- 4. 主畫面顯示 (UI 版面) ---
            st.subheader(f"🎯 {ticker} - 過去 {lookback_years} 年真實領息回測")
            
            if yearly_div.empty:
                st.info("這段期間內沒有配息紀錄喔！")
            else:
                final_cumulative = yearly_div['累計已領股息'].iloc[-1]
                avg_yearly = yearly_div['當年領取總額'].mean()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("持有總股數", f"{total_shares:,} 股")
                c2.metric(f"這 {lookback_years} 年總共領了", f"${final_cumulative:,.0f}")
                c3.metric("平均每年領取", f"${avg_yearly:,.0f}")
                
                st.divider()
                
                # 畫出雙圖表：累計折線圖 + 當年入帳長條圖
                st.subheader("📊 真實歷史軌跡")
                g1, g2 = st.columns(2)
                
                with g1:
                    fig_line = px.line(
                        yearly_div, x="Year", y="累計已領股息", markers=True,
                        title="💰 歷史累計股息雪球滾動圖"
                    )
                    fig_line.update_traces(line=dict(color="#FFC107", width=4), marker=dict(size=10, color="#FF5722"))
                    st.plotly_chart(fig_line, use_container_width=True)
                    
                with g2:
                    fig_bar = px.bar(
                        yearly_div, x="Year", y="當年領取總額",
                        title="💵 每年真實入帳股息 (注意看跳動狀況)",
                        color_discrete_sequence=['#1E88E5']
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                    
                # 顯示詳細數據表
                with st.expander("📝 查看每年真實發放明細"):
                    display_df = yearly_div.copy()
                    display_df['每股配發(元)'] = display_df['Dividends'].round(2)
                    display_df['當年領取總額'] = display_df['當年領取總額'].astype(int)
                    display_df['累計已領股息'] = display_df['累計已領股息'].astype(int)
                    st.dataframe(display_df[['Year', '每股配發(元)', '當年領取總額', '累計已領股息']], use_container_width=True)

    except Exception as e:
        st.error(f"發生錯誤：{e} (可能是網路連線問題，請稍後再試)")
