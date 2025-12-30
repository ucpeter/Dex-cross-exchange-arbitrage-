import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(page_title="Auto-DEX Arb Scanner", layout="wide")

st.title("🔍 Automated Cross-Exchange Scanner")
st.markdown("Scanning live trending tokens for cross-exchange price gaps.")

# --- Sidebar Configuration ---
st.sidebar.header("Scan Settings")
network = st.sidebar.selectbox("Select Network", ["ethereum", "base", "solana", "bsc", "arbitrum", "polygon"])
min_liq = st.sidebar.number_input("Min Liquidity (USD)", value=3000, step=500)
min_profit = st.sidebar.slider("Min Profit Margin (%)", 0.5, 10.0, 1.0)

def get_trending_tokens():
    """Fetches the latest active tokens on DexScreener to scan."""
    # Using the token-profiles endpoint to get 'hot' tokens
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
        return []
    except:
        return []

def get_token_pairs(token_address):
    """Fetches all pools for a specific token address."""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        r = requests.get(url)
        return r.json().get('pairs', []) if r.status_code == 200 else []
    except:
        return []

if st.button("Start Global Scan"):
    status_text = st.empty()
    token_profiles = get_trending_tokens()
    
    if not token_profiles:
        st.error("Could not fetch trending tokens. API might be busy.")
    else:
        all_opportunities = []
        # Filter profiles by selected network
        relevant_tokens = [t for t in token_profiles if t['chainId'] == network]
        
        status_text.info(f"Scanning {len(relevant_tokens)} trending tokens on {network.upper()}...")
        
        progress_bar = st.progress(0)
        
        for i, token in enumerate(relevant_tokens):
            progress_bar.progress((i + 1) / len(relevant_tokens))
            address = token['tokenAddress']
            pairs = get_token_pairs(address)
            
            # Filter pairs by liquidity and network
            valid_pools = []
            for p in pairs:
                liq = float(p.get('liquidity', {}).get('usd', 0))
                if p['chainId'] == network and liq >= min_liq:
                    valid_pools.append({
                        "DEX": p['dexId'].upper(),
                        "Symbol": p['baseToken']['symbol'],
                        "Price": float(p.get('priceUsd', 0)),
                        "Liquidity": liq,
                        "Pair": f"{p['baseToken']['symbol']}/{p['quoteToken']['symbol']}",
                        "URL": p['url']
                    })
            
            # Cross-Exchange Comparison
            if len(valid_pools) >= 2:
                df_temp = pd.DataFrame(valid_pools)
                low_row = df_temp.loc[df_temp['Price'].idxmin()]
                
                # Check for other DEXs
                others = df_temp[df_temp['DEX'] != low_row['DEX']]
                if not others.empty:
                    high_row = others.loc[others['Price'].idxmax()]
                    margin = ((high_row['Price'] - low_row['Price']) / low_row['Price']) * 100
                    
                    # Sanity check: Avoid scams/errors (>50% is usually a honeypot)
                    if margin >= min_profit and margin < 50:
                        all_opportunities.append({
                            "Token": low_row['Symbol'],
                            "Buy At": low_row['DEX'],
                            "Sell At": high_row['DEX'],
                            "Buy Price": low_row['Price'],
                            "Sell Price": high_row['Price'],
                            "Margin": f"{margin:.2f}%",
                            "Liquidity": low_row['Liquidity'],
                            "Link": low_row['URL']
                        })
            
            # Small sleep to respect API rate limits
            time.sleep(0.2)

        status_text.success("Scan Complete!")
        
        if all_opportunities:
            st.subheader(f"💎 Found {len(all_opportunities)} Potential Opportunities")
            results_df = pd.DataFrame(all_opportunities)
            st.dataframe(
                results_df,
                column_config={
                    "Buy Price": st.column_config.NumberColumn(format="$%.8f"),
                    "Sell Price": st.column_config.NumberColumn(format="$%.8f"),
                    "Liquidity": st.column_config.NumberColumn(format="$%,.0f"),
                    "Link": st.column_config.LinkColumn("Action Link")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No cross-exchange gaps found with current liquidity settings.")
        
