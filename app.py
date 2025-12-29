import streamlit as st
import requests
import pandas as pd

# Set Page Config
st.set_page_config(page_title="DEX Arbitrage Scanner", layout="wide")

st.title("🚀 Cross-DEX Arbitrage Scanner")
st.markdown("Scanning real-time prices across decentralized exchanges to find profit gaps.")

# Sidebar Configuration
st.sidebar.header("Scanner Settings")
token_id = st.sidebar.text_input("Enter Token Address (e.g. WETH, PEPE)", "0x6982508145454ce325ddbe47a25d4ec3d2311933")
network_choice = st.sidebar.selectbox("Select Network", ["ethereum", "bsc", "polygon", "arbitrum", "base", "solana"])

def fetch_dex_data(address):
    """Fetch all pools for a specific token address across all DEXs using DexScreener."""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('pairs', [])
        return []
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []

if st.button("Scan for Opportunities"):
    with st.spinner('Scanning DEXs...'):
        pairs = fetch_dex_data(token_id)
        
        if not pairs:
            st.warning("No liquidity pools found for this token address on the selected network.")
        else:
            data = []
            for p in pairs:
                # Filter by selected network
                if p['chainId'] == network_choice:
                    data.append({
                        "DEX": p['dexId'].capitalize(),
                        "Pair": p['baseToken']['symbol'] + "/" + p['quoteToken']['symbol'],
                        "Price (USD)": float(p['priceUsd']),
                        "Liquidity": f"${float(p['liquidity']['usd']):,.0f}" if 'liquidity' in p else "N/A",
                        "Network": p['chainId'].upper(),
                        "URL": p['url']
                    })

            if data:
                df = pd.DataFrame(data)
                
                # Calculate Arbitrage Logic
                min_price_row = df.loc[df['Price (USD)'].idxmin()]
                max_price_row = df.loc[df['Price (USD)'].idxmax()]
                
                buy_dex = min_price_row['DEX']
                sell_dex = max_price_row['DEX']
                buy_price = min_price_row['Price (USD)']
                sell_price = max_price_row['Price (USD)']
                
                profit_margin = ((sell_price - buy_price) / buy_price) * 100

                # Display Results
                col1, col2, col3 = st.columns(3)
                col1.metric("Buy At", buy_dex, f"${buy_price:.6f}")
                col2.metric("Sell At", sell_dex, f"${sell_price:.6f}")
                col3.metric("Profit Margin", f"{profit_margin:.2f}%", delta_color="normal")

                st.subheader("All Live Price Feeds")
                st.dataframe(df.sort_values(by="Price (USD)"), use_container_width=True)
                
                st.info(f"💡 **Strategy:** Buy on **{buy_dex}** and sell on **{sell_dex}**. Ensure you have enough gas for the **{network_choice.upper()}** network.")
            else:
                st.error("No matching pools found for the selected network.")

st.divider()
st.caption("Data provided by DexScreener API. Prices include 1-minute caching.")
