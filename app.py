import streamlit as st
import streamlit.components.v1 as components
import eurostat
import pandas as pd

@st.cache_data(ttl=3600)
def get_cee_energy_inflation():
    countries = ['PL', 'HU', 'CZ', 'RO', 'SK']
    params = {'coicop': ['CP045', 'CP0722'], 'geo': countries}
    
    df = eurostat.get_data_df('prc_hicp_midx', filter_pars=params)

    # 1. Identify which columns are NOT dates (the ID columns)
    # Eurostat date columns usually look like '2024M01' or '2023-01'
    # ID columns are usually 'unit', 'coicop', 'geo\time', etc.
    id_vars = [col for col in df.columns if not any(char.isdigit() for char in str(col))]
    
    # 2. Perform the melt using the detected ID columns
    df_long = df.melt(id_vars=id_vars, var_name='date', value_name='index_value')
    
    # 3. Standardize the Geo column name (Eurostat often uses 'geo\\time' or 'geo')
    # We rename it to 'geo' for consistency in the rest of the app
    geo_col = next((c for c in id_vars if 'geo' in c.lower()), None)
    if geo_col:
        df_long = df_long.rename(columns={geo_col: 'geo'})

    # 4. Date conversion and Inflation calculation
    df_long['date'] = pd.to_datetime(df_long['date'].str.replace('M', '-'), format='%Y-%m')
    df_long = df_long.sort_values(['geo', 'coicop', 'date'])
    
    # Calculate YoY
    df_long['yoy_inflation'] = df_long.groupby(['geo', 'coicop'])['index_value'].pct_change(12) * 100
    
    return df_long
    
def tradingview_energy_widget():
    # Embed code from TradingView for Brent Oil and Natural Gas
    # You can customize the symbols (UKOIL for Brent, NG1! for Gas)
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

# In your app:
st.title("Energy Shock Monitor: CEE Inflation Impact")
tradingview_energy_widget()

st.sidebar.header("Sensitivity Analysis")
oil_price_shock = st.sidebar.slider("Oil Price Increase ($)", 0, 50, 10)

# Simplified macro assumption: A $10/bbl rise adds ~0.4% to CEE CPI 
# depending on government energy caps.
cpi_impact = oil_price_shock * 0.04 

st.metric("Estimated CEE CPI Impact", f"+{cpi_impact:.2f}%", delta="Inflationary", delta_color="inverse")

with st.expander("Regional Vulnerability Notes"):
    st.write("""
    * **Poland:** High reliance on coal but gas is the marginal price setter for industry.
    * **Hungary:** High exposure to gas; Forint (HUF) volatility amplifies the energy shock.
    * **Czechia:** Energy-intensive industrial base makes PPI very sensitive to gas surges.
    """)

def plot_energy_pass_through(df, country_code):
    subset = df[df['geo\\time'] == country_code]
    
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

data = get_cee_energy_inflation()
plot_energy_pass_through(data, selected_country)
