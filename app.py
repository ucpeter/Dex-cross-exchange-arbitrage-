import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Cross-DEX Arb Scanner Pro", layout="wide")

st.title(" Dex Arbitrage Scanner")

# --- Sidebar Configuration ---
st.sidebar.header("Filter Settings")
token_id = st.sidebar.text_input("Token Address (e.g. NPC)", "0x8ed706248571833894e117445228a279dd704bb9")
min_liq = st.sidebar.number_input("Min Liquidity (USD)", value=5000, step=1000)
network = st.sidebar.selectbox("Network", ["ethereum", "base", "solana", "bsc", "arbitrum"])

def fetch_pairs(address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
    try:
        r = requests.get(url)
        return r.json().get('pairs', []) if r.status_code == 200 else []
    except:
        return []

if st.button("Scan Cross-Exchange"):
    pairs = fetch_pairs(token_id)
    
    if not pairs:
        st.error("No data found.")
    else:
        results = []
        for p in pairs:
            # Filter by network and liquidity
            liq = float(p.get('liquidity', {}).get('usd', 0))
            if p['chainId'] == network and liq >= min_liq:
                results.append({
                    "DEX": p['dexId'].upper(),
                    "Pair": f"{p['baseToken']['symbol']}/{p['quoteToken']['symbol']}",
                    "Price": float(p.get('priceUsd', 0)),
                    "Liquidity": liq,
                    "Link": p['url']
                })

        if len(results) >= 2:
            df = pd.DataFrame(results)
            
            # --- CROSS-EXCHANGE LOGIC ---
            # Find the absolute minimum price
            low_row = df.loc[df['Price'].idxmin()]
            
            # Filter out any other pools that are on the SAME DEX as the low price
            other_dex_df = df[df['DEX'] != low_row['DEX']]
            
            if not other_dex_df.empty:
                # Find the highest price on a DIFFERENT exchange
                high_row = other_dex_df.loc[other_dex_df['Price'].idxmax()]
                margin = ((high_row['Price'] - low_row['Price']) / low_row['Price']) * 100

                # Metrics Display
                c1, c2, c3 = st.columns(3)
                c1.metric("BUY AT", f"{low_row['DEX']} ({low_row['Pair']})", f"${low_row['Price']:.8f}")
                c2.metric("SELL AT", f"{high_row['DEX']} ({high_row['Pair']})", f"${high_row['Price']:.8f}")
                c3.metric("CROSS-DEX MARGIN", f"{margin:.2f}%")

                # Results Table with Proper Formatting
                st.subheader("Liquidity Pools Comparison")
                st.dataframe(
                    df.sort_values("Price"),
                    column_config={
                        "Price": st.column_config.NumberColumn("Price (USD)", format="$%.8f"),
                        "Liquidity": st.column_config.NumberColumn("Liquidity (USD)", format="$%,.0f"),
                        "Link": st.column_config.LinkColumn("Pool URL")
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("Found multiple pools, but they are all on the same exchange (e.g. all on Uniswap). Cross-exchange arbitrage is not possible.")
        else:
            st.info("Not enough high-liquidity pools found on different exchanges.")

