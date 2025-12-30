import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(page_title="Deep Arb Scanner", layout="wide")

st.title("🛡️ Deep Liquidity Arb Scanner")

# --- Optimized Sidebar ---
network = st.sidebar.selectbox("Network", ["base", "solana", "ethereum", "bsc", "arbitrum"])
min_liq = st.sidebar.slider("Min Liquidity ($)", 1000, 50000, 5000)
min_margin = st.sidebar.slider("Min Margin (%)", 0.5, 5.0, 1.0)

def fetch_latest_pairs(chain):
    """Gets the newest pairs launched in the last few hours."""
    url = f"https://api.dexscreener.com/token-boosts/latest/v1" # Scanning boosted/active tokens
    try:
        r = requests.get(url)
        if r.status_code == 200:
            # Filter for your specific chain immediately
            return [t for t in r.json() if t.get('chainId') == chain]
        return []
    except:
        return []

def get_all_pools(address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
    try:
        r = requests.get(url)
        return r.json().get('pairs', []) if r.status_code == 200 else []
    except:
        return []

if st.button("Run Deep Scan"):
    latest = fetch_latest_pairs(network)
    if not latest:
        st.warning(f"No active boosted tokens found on {network} right now. Try another network.")
    else:
        results = []
        progress = st.progress(0)
        
        for i, entry in enumerate(latest[:30]): # Scan top 30 active tokens
            progress.progress((i + 1) / 30)
            addr = entry.get('tokenAddress')
            pools = get_all_pools(addr)
            
            valid_pools = []
            for p in pools:
                liq = float(p.get('liquidity', {}).get('usd', 0))
                if p['chainId'] == network and liq >= min_liq:
                    valid_pools.append({
                        "DEX": p['dexId'].upper(),
                        "Symbol": p['baseToken']['symbol'],
                        "Price": float(p.get('priceUsd', 0)),
                        "Liquidity": liq,
                        "Pair": f"{p['baseToken']['symbol']}/{p['quoteToken']['symbol']}"
                    })

            if len(valid_pools) >= 2:
                df_p = pd.DataFrame(valid_pools)
                low = df_p.loc[df_p['Price'].idxmin()]
                others = df_p[df_p['DEX'] != low['DEX']]
                
                if not others.empty:
                    high = others.loc[others['Price'].idxmax()]
                    gap = ((high['Price'] - low['Price']) / low['Price']) * 100
                    
                    if gap >= min_margin and gap < 30: # Filter out crazy scam gaps
                        results.append({
                            "Token": low['Symbol'],
                            "Buy At": low['DEX'],
                            "Sell At": high['DEX'],
                            "Margin": f"{gap:.2f}%",
                            "Liquidity": f"${low['Liquidity']:,.0f}",
                            "Pairs": f"{low['Pair']} vs {high['Pair']}"
                        })
            time.sleep(0.1) # Prevent API ban

        if results:
            st.success(f"Found {len(results)} potential gaps!")
            st.table(results)
        else:
            st.error("No cross-DEX gaps found. Market is currently balanced.")
            
