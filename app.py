import streamlit as st
import streamlit.components.v1 as components

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
