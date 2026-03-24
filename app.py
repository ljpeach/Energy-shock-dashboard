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
# --- Configuration ---
# NRG_BAL: IC_OBS (Inland Consumption), SIEC: G3000 (Natural Gas)
URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_cb_gasm?format=JSON&lang=EN&nrg_bal=IC_OBS&siec=G3000&unit=MIO_M3"

@st.cache_data(ttl=3600)
def get_macro_data():
    response = requests.get(URL)
    data = response.json()
    
    # 1. Extract Dimensions
    # The 'index' in JSON-stat maps the position in the 'value' dict to a category
    time_dims = data['dimension']['time']['category']['label']
    geo_dims = data['dimension']['geo']['category']['label']
    
    # 2. Extract Values safely
    # Eurostat returns a dict where key is the index (string) and value is the number
    values_dict = data['value']
    
    # 3. Create a pivot-ready list
    records = []
    # This nested loop ensures we align every Geo and Time period correctly
    for geo_idx, geo_label in enumerate(data['dimension']['geo']['category']['index']):
        for time_idx, time_label in enumerate(data['dimension']['time']['category']['index']):
            # Eurostat uses a linear index: (geo_index * num_times) + time_index
            internal_idx = str(geo_idx * len(time_dims) + time_idx)
            
            val = values_dict.get(internal_idx, None) # Use None if missing
            
            records.append({
                "Entity": geo_dims[geo_label],
                "Period": time_label,
                "Value": val
            })
            
    df = pd.DataFrame(records)
    df['Period'] = pd.to_datetime(df['Period'], format='%Y-%M', errors='coerce')
    return df.dropna(subset=['Value'])

# --- App Interface ---
st.set_page_config(layout="wide", page_title="Energy Shock Monitor")
st.title("Macro Analysis: Israel-Iran Energy Shock")

try:
    raw_df = get_macro_data()
    
    # Sidebar Filters
    target_geo = st.sidebar.selectbox("Select Economy", raw_df['Entity'].unique(), index=10)
    price_shock = st.sidebar.slider("TTF Gas Price Shock (%)", 0, 500, 100)
    
    analysis_df = raw_df[raw_df['Entity'] == target_geo].sort_values('Period')

    # --- Metrics Section ---
    col1, col2, col3 = st.columns(3)
    
    # Heuristic: Energy Intensity of GDP (Simplified for demo)
    # In a real model, you'd pull GDP (nama_10_gdp) to normalize this.
    latest_vol = analysis_df['Value'].iloc[-1]
    est_bill_increase = (latest_vol * (price_shock/100)) * 0.0008 # Dummy multiplier for EUR billions
    
    col1.metric("Latest Monthly Consumption", f"{latest_vol:,.0f} Mio m3")
    col2.metric("Estimated Monthly Bill Delta", f"€{est_bill_increase:.2f}B", delta=f"{price_shock}% shock")
    col3.metric("Current Account Risk", "High" if price_shock > 50 else "Moderate")

    # --- Charting ---
    fig = px.area(analysis_df, x='Period', y='Value', 
                  title=f"Baseline Natural Gas Consumption: {target_geo}",
                  labels={"Value": "Mio m3", "Period": "Time"})
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Mapping Error: {e}")
    st.info("This usually happens when the API index doesn't match the dimension count. The logic above fixes this by using .get() on the value dictionary.")
