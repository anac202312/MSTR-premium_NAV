import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
def get_shares_full_auto():
    print("⏳ 嘗試使用 yfinance 輕量級 API 獲取最新股數...")
    try:
        # 建立 Ticker 物件
        ticker = yf.Ticker("MSTR")
        
        shares = ticker.fast_info['shares']
        
        # 確保抓下來的數字是合理的（大於 1 億股，確認是分割後的數字）
        if shares > 100000000:
            return shares
        else:
            raise ValueError(f"抓到的股數異常: {shares}")
            
    except Exception as e:
        print(f"⚠️ 自動抓取失敗: {e}，使用備援預設值。")
        # 如果被擋，回傳最新財報的 3.4 億股
        return 340000000
    
# --- 頁面設定 ---
st.set_page_config(page_title="DAT.co Premium to NAV", layout="wide")

# MSTR 近期持有的比特幣總量
MSTR_BTC_HOLDINGS = 766970  

st.title("📊 MicroStrategy (MSTR) Premium to NAV 監控儀表板")
st.markdown("""
這個平台追蹤最著名的 DAT.co 公司 **MicroStrategy** 的資產淨值溢價 (Premium to NAV)。
* **公式計算**：`Premium = (MSTR 股價 - 每股 NAV) / 每股 NAV * 100%`
* **指標意義**：反映傳統金融市場對比特幣的情緒。溢價越高，代表市場越 FOMO（錯失恐懼）；溢價縮小或折價，代表市場情緒冷卻。
""")

@st.cache_data(ttl=3600)
def load_and_process_data(days):
    # 抓取價格資料 (使用yfinance) 
    print("⏳ 抓取 MSTR 與 BTC 價格...")
    data = yf.download(["MSTR", "BTC-USD"], period=f"{days}d", timeout=10)
    if data.empty:
        st.error("無法取得價格資料。")
        return pd.DataFrame()
    
    mstr_history = data['Close']['MSTR']
    btc_history = data['Close']['BTC-USD']

    # 自動抓取最新股數
    try:
        shares_out = get_shares_full_auto()
        print(f"🎯 成功從 FMP API 獲取最新股數: {shares_out}")
    except Exception as e:
        # 如果 FMPAPI失敗，使用分割後的預設值作為備案
        shares_out = 340000000 
        print(f"⚠️ FMP API 抓取失敗: {e}，使用最新財報作為預設值。")

    # 計算邏輯
    df = pd.DataFrame({'MSTR_Price': mstr_history, 'BTC_Price': btc_history}).dropna()
    df['NAV_Total'] = df['BTC_Price'] * MSTR_BTC_HOLDINGS
    df['NAV_Per_Share'] = df['NAV_Total'] / shares_out
    df['Premium_Percent'] = ((df['MSTR_Price'] - df['NAV_Per_Share']) / df['NAV_Per_Share']) * 100
    
    # 整理日期格式
    df.reset_index(inplace=True)
    df.rename(columns={'Date': '日期'}, inplace=True)
    df['日期'] = df['日期'].dt.strftime('%Y-%m-%d')
    
    return df
    
st.sidebar.header("儀表板設定")
days_to_show = st.sidebar.slider("選擇歷史資料天數", min_value=30, max_value=365, value=90)

df = load_and_process_data(days_to_show)

if not df.empty:
    latest_premium = df['Premium_Percent'].iloc[-1]
    latest_mstr = df['MSTR_Price'].iloc[-1]
    
    col1, col2 = st.columns(2)
    col1.metric("最新 MSTR 股價", f"${latest_mstr:.2f}")
    col2.metric("最新 Premium to NAV", f"{latest_premium:.2f}%")

    # 時間序列圖表
    fig = px.line(df, x='日期', y='Premium_Percent', 
                  title=f"過去 {days_to_show} 天 MSTR 溢價走勢 (%)",
                  labels={'Premium_Percent': '溢價比例 (%)'})
    fig.add_hline(y=0, line_dash="dash", line_color="red") # 0% 基準線
    st.plotly_chart(fig, use_container_width=True)

    
