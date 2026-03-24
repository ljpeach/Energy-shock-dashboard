import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import requests
import plotly.express as px
import eurostat
import pandas as pd
import yfinance as yf
   
def tradingview_energy_widget():
    html_code = """
    <div class="tradingview-widget-container">
      <div id="tradingview_energy"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.MediumWidget({
        "symbols": [
          ["Brent Oil", "TVC:UKOIL|12M"],
          ["Natural Gas", "NYMEX:NG1!|12M"]
        ],
        "chartOnly": false,
        "width": "100%",
        "height": 400,
        "locale": "en",
        "colorTheme": "dark",
        "autosize": true,
        "showVolume": false,
        "hideDateRanges": false,
        "scalePosition": "right",
        "scaleMode": "Normal",
        "fontFamily": "Arial, sans-serif",
        "noOverlays": false,
        "container_id": "tradingview_energy"
      });
      </script>
    </div>
    """
    components.html(html_code, height=420)

@st.cache_data(ttl=3600)
def get_cee_macro_data(dataset_code='prc_hicp_midx'):
    countries = ['PL', 'HU', 'CZ', 'RO', 'SK']
    if dataset_code == 'prc_hicp_midx':
        cpi_components = ['CP045', 'CP0722']
        parameters = {'coicop': cpi_components, 'geo': countries}
    elif dataset_code == 'nrg_ti_m':
        energy_imports = ['G3000', 'O4000', 'E7000']
        parameters = {'siec': energy_imports, 'geo': countries, 'unit': 'TJ_GCV'}
    else:
        parameters = {'geo': countries}

    df = eurostat.get_data_df(dataset_code, filter_pars=parameters)
    df = df.rename(columns=lambda x: 'geo' if 'geo' in x.lower() else x)
    id_vars = [col for col in df.columns if not any(char.isdigit() for char in str(col))]
    df_long = df.melt(id_vars=id_vars, var_name='date', value_name='value')
    df_long['date'] = pd.to_datetime(df_long['date'].str.replace('M', '-'), format='%Y-%m')
    
    return df_long

# ----------------------------------------------------
# -------------------- APP LAYOUT --------------------
# ----------------------------------------------------
st.title("Energy Shock Monitor")
tradingview_energy_widget()

st.sidebar.header("Sensitivity Analysis")
oil_price_shock = st.sidebar.slider("Oil Price Increase ($)", 0, 50, 10)

# Simplified macro assumption: A $10/bbl rise adds ~0.4% to CEE CPI 
# depending on government energy caps.
cpi_impact = oil_price_shock * 0.04 

st.metric("Estimated CEE CPI Impact", f"+{cpi_impact:.2f}%", delta="Inflationary", delta_color="inverse")

def plot_energy_pass_through(df, country_code):
    # Use the standardized 'geo' name here
    subset = df[df['geo'] == country_code]
    
    fig = go.Figure()
    
    # Utility Channel
    utils = subset[subset['coicop'] == 'CP045']
    fig.add_trace(go.Scatter(x=utils['date'], y=utils['yoy_inflation'], 
                             name="Utility Bills (YoY %)", line=dict(color='#A8DADC')))
    
    # Fuel Channel
    fuel = subset[subset['coicop'] == 'CP0722']
    fig.add_trace(go.Scatter(x=fuel['date'], y=fuel['yoy_inflation'], 
                             name="Pump Prices (YoY %)", line=dict(color='#E63946', width=3)))
    
    fig.update_layout(
        title=f"<b>{country_code} Energy Inflation Channels</b>",
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white")
    )
    st.plotly_chart(fig, use_container_width=True)

# UI Logic
st.sidebar.title("CEE Region Selector")
selected_country = st.sidebar.selectbox("Select Country", ['PL', 'HU', 'CZ', 'RO'])

#data = get_cee_macro_data('prc_hicp_midx')
#plot_energy_pass_through(data, selected_country)

def get_brent_prices():
    # Fetch daily data for the last 2 years
    brent = yf.Ticker("BZ=F")
    df = brent.history(period="2y")
    return df[['Close']].rename(columns={'Close': 'Brent_Price'})

brent_data = get_brent_prices()
st.line_chart(brent_data)

#brent_monthly = brent_data.resample('MS').mean()
#merged_df = pd.merge(brent_monthly, df_long, left_index=True, right_on='date')
#st.line_chart(merged_df)






#################################

# Eurostat API Config
BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
DATASET_CODE = "nrg_cb_gasm"

def fetch_eurostat_data(geo="EU27_2020", unit="MIO_M3"):
    """
    Fetches Natural Gas Monthly Balance data.
    NRG_BAL: IC_OBS (Inland Consumption), IMP (Imports), EXP (Exports)
    """
    # Simplified query parameters for the API
    params = f"{DATASET_CODE}?format=JSON&lang=EN&geo={geo}&unit={unit}&nrg_bal=IC_OBS&siec=G3000"
    
    try:
        response = requests.get(BASE_URL + params)
        response.raise_for_status()
        data = response.json()
        
        # Extracting dimensions and values
        # Note: For production, consider using 'eurostatapiclient' or 'pandas_dmx' 
        # for more robust parsing of JSON-stat structures.
        values = data['value']
        index = data['dimension']['time']['category']['label']
        
        df = pd.DataFrame({
            'Period': list(index.values()),
            'Consumption': list(values.values())
        })
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- Streamlit UI ---
st.set_page_config(page_title="Macro Energy Shock Analyzer", layout="wide")

st.title("🇮🇱🇮🇷 Energy Shock Impact: EU Macro Monitor")
st.sidebar.header("Model Parameters")

# Scenario Inputs
shock_magnitude = st.sidebar.slider("Gas Price Surge (%)", 0, 300, 50)
pass_through = st.sidebar.slider("Cost Pass-through to CPI (%)", 0.0, 1.0, 0.4)

st.markdown("""
### 1. Natural Gas Consumption Trends (Eurostat)
This baseline shows the current inland consumption ($IC\_OBS$) which serves as the exposure metric for your shock scenario.
""")

df_gas = fetch_eurostat_data()

if not df_gas.empty:
    fig = px.line(df_gas, x='Period', y='Consumption', 
                 title="Monthly Inland Gas Consumption (Mio m3)",
                 template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # --- Analytical Overlay ---
    st.subheader("2. Impact Assessment: Firm Profitability & Households")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("**Supply-Side: Industry Impact**")
        impact = shock_magnitude * 0.12 # Simplified coefficient for margin erosion
        st.metric("Estimated Margin Compression (Ind. Avg)", f"-{impact:.2f}%")
        st.write("High-gas intensity sectors (Chemicals, Glass, Steel) will see non-linear investment delays.")

    with col2:
        st.info("**Demand-Side: Household Bills**")
        real_income_hit = (shock_magnitude * pass_through) / 10
        st.metric("Real Disposable Income Delta", f"-{real_income_hit:.2f}%")
        st.write("This scales the 'External Account' deficit via the energy trade balance.")
