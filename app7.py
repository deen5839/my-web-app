import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# --- 1. 網頁初始設定 ---
st.set_page_config(page_title="存股複利雪球 2.0", page_icon="🔥", layout="wide")

st.title("🔥 存股複利雪球 2.0 (真實歷史逐年累計版)")
st.markdown("連線華爾街資料庫，用『每年真實發放的股息』算給你聽！")

# --- 2. 側邊欄輸入設定 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    ticker = st.text_input("股票代號 (台股請加 .TW)", value="1218.TW")
    stock_sheets = st.number_input("持有張數 (1張=1000股)", value=226, min_value=1, step=1)
    
    start_year = st.number_input("歷史回測起始年份", value=2015, min_value=2000, max_value=2030, step=1)
    years_to_calc = st.slider("想要計算幾年？(最長20年)", min_value=1, max_value=20, value=12)
    
    st.divider()
    st.subheader("🛠️ 最新年度 (2026) 股息手動校正")
    # 💡 增加一個勾選框：預設不勾選（自動抓取該股票配息）；需要手動修改時再勾選
    enable_manual = st.checkbox("手動指定 2026 年配息金額", value=False)
    manual_2026_div = st.number_input("2026年每股配息 (元)", value=1.32, step=0.01, format="%.2f")

total_shares = stock_sheets * 1000

# --- 3. 核心 API 串接與計算邏輯 ---
with st.spinner(f"📡 正在從全球金融資料庫撈取 {ticker} 的歷史配息..."):
    try:
        stock = yf.Ticker(ticker)
        div_data = stock.dividends
        
        if div_data.empty:
            st.warning(f"⚠️ 找不到 {ticker} 的配息資料，請檢查代號是否正確 (台股記得加 .TW)。")
        else:
            # 整理 Yahoo Finance 資料
            df_div = pd.DataFrame(div_data).reset_index()
            df_div['Date'] = pd.to_datetime(df_div['Date'], utc=True).dt.tz_convert('Asia/Taipei')
            df_div['Year'] = df_div['Date'].dt.year
            
            # 按年份加總歷史配息 (自動抓取該股票各年份真實股息)
            yearly_div_raw = df_div.groupby('Year')['Dividends'].sum().reset_index()
            
            # 建立完整的年份序列
            end_year = start_year + years_to_calc - 1
            full_years = pd.DataFrame({'Year': list(range(start_year, end_year + 1))})
            
            # 合併歷史資料
            yearly_div = pd.merge(full_years, yearly_div_raw, on='Year', how='left').fillna(0)
            
            current_year = datetime.now().year # 2026
            
            # 💡 核心修正邏輯：
            # 1. 如果勾選了手動校正，才把 2026 年蓋成手動金額；沒勾選就直接用 yfinance 抓到的台積電/其他股票真實數字！
            if enable_manual:
                yearly_div.loc[yearly_div['Year'] == current_year, 'Dividends'] = manual_2026_div
                latest_div = manual_2026_div
            else:
                # 如果 yfinance 有抓到 2026 數字就用抓到的，否則拿最近一年的真實配息
                real_2026 = yearly_div.loc[yearly_div['Year'] == current_year, 'Dividends'].values
                if len(real_2026) > 0 and real_2026[0] > 0:
                    latest_div = real_2026[0]
                else:
                    # 抓最近一個非 0 的真實配息作為未來推算基準
                    valid_divs = yearly_div[yearly_div['Dividends'] > 0]['Dividends']
                    latest_div = valid_divs.iloc[-1] if not valid_divs.empty else 0
            
            # 2. 未來年份 (> 2026) 自動延續『該股票最新/校正後的股息』往後推算
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
                
                # 將序號改成從 1 開始
                display_df.index = range(1, len(display_df) + 1)
                st.dataframe(display_df[['Year', '每股配發(元)', '当年領取總額', '累計已領股息']], use_container_width=True)

    except Exception as e:
        st.error(f"發生錯誤：{e}")
