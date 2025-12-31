import streamlit as st
import requests
import time

# --- Settings ---
st.set_page_config(page_title="Flashloan Arb Finder", layout="wide")
st.title("⚡ Furucombo Flashloan Scanner")

# Furucombo mainly supports these on Ethereum
NETWORKS = ["ethereum", "polygon", "arbitrum"]
network = st.sidebar.selectbox("Network", NETWORKS)
min_profit_usd = st.sidebar.number_input("Min Profit After Gas ($)", value=50)

def scan_dex_pairs():
    # Using DexScreener's Latest Pairs for high-frequency updates
    url = f"https://api.dexscreener.com/token-boosts/latest/v1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            tokens = [t for t in response.json() if t['chainId'] == network]
            return tokens
        return []
    except:
        return []

def get_pair_prices(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        res = requests.get(url).json()
        return res.get('pairs', [])
    except:
        return []

if st.button("Search for Executable Combos"):
    with st.spinner("Scanning Mempool-adjacent data..."):
        trending = scan_dex_pairs()
        found = []
        
        for token in trending[:15]: # Scan top 15 most active tokens
            pairs = get_pair_prices(token['tokenAddress'])
            
            # Filter for Furucombo-supported DEXs
            # Furucombo supports: UNISWAP, SUSHISWAP, QUICKswap, KYBER
            valid_pools = [p for p in pairs if p['dexId'] in ['uniswap', 'sushiswap', 'quickswap', 'kyber']]
            
            if len(valid_pools) >= 2:
                # Compare lowest and highest
                low = min(valid_pools, key=lambda x: float(x['priceUsd']))
                high = max(valid_pools, key=lambda x: float(x['priceUsd']))
                
                price_diff = float(high['priceUsd']) - float(low['priceUsd'])
                margin_pct = (price_diff / float(low['priceUsd'])) * 100
                
                # Flashloan Check: Profit must cover 0.09% fee + High Gas
                if margin_pct > 0.5: # 0.5% is a realistic minimum for flashloans
                    found.append({
                        "Token": token['baseToken']['symbol'],
                        "Buy DEX": low['dexId'].upper(),
                        "Sell DEX": high['dexId'].upper(),
                        "Margin": f"{margin_pct:.2f}%",
                        "Liquidity": f"${float(low['liquidity']['usd']):,.0f}",
                        "Address": token['tokenAddress']
                    })
        
        if found:
            st.success(f"Found {len(found)} potential combos!")
            st.table(found)
            st.info("💡 **Next Step:** Copy the Address to Furucombo, add a 'Flashloan' cube, then 'Swap' cubes for the Buy/Sell DEXs.")
        else:
            st.warning("No significant gaps found. Markets are currently efficient.")
    
