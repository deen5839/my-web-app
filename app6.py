import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. 網頁初始設定 ---
st.set_page_config(page_title="存股複利雪球儀表板", page_icon="📈", layout="wide")

st.title("📈 專屬存股複利雪球儀表板")
st.markdown("看著資產一年年長大，這就是時間的魔法！✨")

# --- 2. 側邊欄輸入設定 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    stock_name = st.text_input("股票名稱", value="泰山 1218")
    stock_sheets = st.number_input("持有張數 (1張=1000股)", value=226, min_value=1, step=1)
    stock_price = st.number_input("目前股價 (元)", value=19.2, min_value=0.0, step=0.1)
    annual_dividend = st.number_input("預估每年每股配息 (元)", value=1.32, min_value=0.0, step=0.1)
    years = st.slider("試算年限 (年)", min_value=1, max_value=20, value=10)

# --- 3. 核心計算邏輯 ---
total_shares = stock_sheets * 1000
base_market_value = total_shares * stock_price
annual_dividend_total = total_shares * annual_dividend

# 建立一個清單來儲存每一年的數據
data = []
cumulative_dividend = 0

for year in range(1, years + 1):
    cumulative_dividend += annual_dividend_total
    total_asset = base_market_value + cumulative_dividend
    
    data.append({
        "第幾年": f"第 {year} 年",
        "當年股息": annual_dividend_total,
        "累計已領股息": cumulative_dividend,
        "總資產市值": total_asset
    })

# 轉換成 Pandas DataFrame 方便畫圖與展示
df = pd.DataFrame(data)

# --- 4. 主畫面顯示 (UI 版面) ---
st.subheader(f"🎯 {stock_name} - {years} 年期試算結果")

# 取出最後一年的最終數據
final_cumulative_dividend = df.iloc[-1]["累計已領股息"]
final_total_asset = df.iloc[-1]["總資產市值"]

# 顯示三個大大的 Metric，字體跟排版 Streamlit 會自動處理得很漂亮
col1, col2, col3 = st.columns(3)
col1.metric(label="股票總市值 (本金)", value=f"${base_market_value:,.0f}")
col2.metric(label=f"{years} 年後累計總股息", value=f"${final_cumulative_dividend:,.0f}")
col3.metric(label=f"{years} 年後總資產", value=f"${final_total_asset:,.0f}", delta=f"+{final_cumulative_dividend:,.0f} 純收益")

st.divider()

# 畫出漂亮的折線圖
st.subheader("📊 累計股息成長曲線")
fig = px.line(
    df, 
    x="第幾年", 
    y="累計已領股息", 
    markers=True, 
    title="時間就是金錢：股息雪球滾動圖",
    labels={"累計已領股息": "金額 (台幣)"}
)

# 稍微美化一下線條跟點的顏色，讓質感升級
fig.update_traces(line=dict(color="#1E88E5", width=4), marker=dict(size=10, color="#FFC107"))
st.plotly_chart(fig, use_container_width=True)

# (加碼贈送) 顯示詳細數據表，方便核對數字
with st.expander("📝 查看每年詳細數據明細"):
    st.dataframe(df, use_container_width=True)
