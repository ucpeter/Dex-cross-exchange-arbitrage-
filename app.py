import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Pro DEX Arb Scanner", layout="wide")

st.title("⚖️ Pro Cross-DEX Arbitrage Scanner")
st.markdown("Comparing prices normalized to USD to find executable gaps.")

# Sidebar Settings
st.sidebar.header("Filter Settings")
token_id = st.sidebar.text_input("Token Address", "0x6982508145454ce325ddbe47a25d4ec3d2311933") # PEPE default
min_liq = st.sidebar.number_input("Min Liquidity (USD)", value=5000, step=1000)
network_choice = st.sidebar.selectbox("Network", ["ethereum", "bsc", "base", "arbitrum", "solana"])

def fetch_data(address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('pairs', [])
        return []
    except:
        return []

if st.button("Scan for Real Trades"):
    pairs = fetch_data(token_id)
    
    if not pairs:
        st.error("No data found for this token.")
    else:
        processed_data = []
        for p in pairs:
            # 1. Filter by Network
            if p['chainId'] != network_choice:
                continue
                
            # 2. Extract USD values (DexScreener normalizes these for us)
            usd_price = float(p.get('priceUsd', 0))
            liquidity = float(p.get('liquidity', {}).get('usd', 0))
            
            # 3. Filter out "Ghost" pools (Liquidity too low to trade)
            if liquidity < min_liq:
                continue

            processed_data.append({
                "DEX": p['dexId'].upper(),
                "Pair": p['baseToken']['symbol'] + "/" + p['quoteToken']['symbol'],
                "Price (USD)": usd_price,
                "Liquidity": liquidity,
                "Link": p['url']
            })

        if len(processed_data) > 1:
            df = pd.DataFrame(processed_data)
            
            # Identify Best Prices
            low_row = df.loc[df['Price (USD)'].idxmin()]
            high_row = df.loc[df['Price (USD)'].idxmax()]
            
            margin = ((high_row['Price (USD)'] - low_row['Price (USD)']) / low_row['Price (USD)']) * 100

            # UI Display
            c1, c2, c3 = st.columns(3)
            c1.metric("Buy At", low_row['DEX'], f"${low_row['Price (USD)']:,.8f}")
            c2.metric("Sell At", high_row['DEX'], f"${high_row['Price (USD)']:,.8f}")
            c3.metric("Gross Profit", f"{margin:.2f}%")

            if margin > 15:
                st.warning("⚠️ High margin (>15%) often indicates a 'Honeypot' or tax token. Proceed with caution.")
            elif margin > 0.5:
                st.success(f"✅ Potential Opportunity Found on {network_choice.upper()}!")

            st.subheader("Comparison Table (Normalized to USD)")
            st.dataframe(df.sort_values("Price (USD)"), use_container_width=True)
        else:
            st.info("Not enough high-liquidity pools found to compare. Try lowering 'Min Liquidity'.")
            
