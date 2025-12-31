
import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Pro Arb Scanner v2", layout="wide")

st.title("⚖️ Accurate Cross-DEX Scanner")

# --- Sidebar ---
st.sidebar.header("Scan Parameters")
token_id = st.sidebar.text_input("Token Address", "0x6982508145454ce325ddbe47a25d4ec3d2311933")
min_liq = st.sidebar.number_input("Minimum Liquidity ($)", value=2000, step=500)
network_choice = st.sidebar.selectbox("Blockchain", ["ethereum", "bsc", "base", "arbitrum", "solana"])

def fetch_data(address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
    try:
        r = requests.get(url)
        return r.json().get('pairs', []) if r.status_code == 200 else []
    except:
        return []

if st.button("Find Real Opportunities"):
    pairs = fetch_data(token_id)
    
    if not pairs:
        st.error("No pools found.")
    else:
        results = []
        for p in pairs:
            # Filter by network
            if p['chainId'] != network_choice:
                continue
            
            liq = float(p.get('liquidity', {}).get('usd', 0))
            price_usd = float(p.get('priceUsd', 0))
            
            # 1. Skip if price or liquidity is missing/too low
            if liq < min_liq or price_usd == 0:
                continue

            results.append({
                "DEX": p['dexId'].upper(),
                "Pair": f"{p['baseToken']['symbol']}/{p['quoteToken']['symbol']}",
                "Price": price_usd,
                "Liquidity": liq,
                "Link": p['url']
            })

        if len(results) >= 2:
            df = pd.DataFrame(results)
            
            # Find Min/Max but filter out "Impossible" Gaps (>100% profit)
            low_row = df.loc[df['Price'].idxmin()]
            high_row = df.loc[df['Price'].idxmax()]
            margin = ((high_row['Price'] - low_row['Price']) / low_row['Price']) * 100

            # --- Results Display ---
            if margin > 100:
                st.error(f"Filtered out a {margin:.0f}% gap - Likely a pricing error or scam.")
            else:
                col1, col2, col3 = st.columns(3)
                col1.metric("BUY AT", f"{low_row['DEX']} ({low_row['Pair']})", f"${low_row['Price']:,.8f}")
                col2.metric("SELL AT", f"{high_row['DEX']} ({high_row['Pair']})", f"${high_row['Price']:,.8f}")
                col3.metric("GROSS MARGIN", f"{margin:.2f}%")
                
                # Show formatted table
                st.subheader("All Valid Liquidity Pools")
                st.dataframe(
                    df.sort_values("Price"),
                    column_config={
                        "Price": st.column_config.NumberColumn("Price (USD)", format="$%.8f"),
                        "Liquidity": st.column_config.NumberColumn("Liquidity (USD)", format="$%,.2f"),
                        "Link": st.column_config.LinkColumn("DEX Link")
                    },
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("Found data, but not enough pairs met your 'Min Liquidity' filter.")
            
