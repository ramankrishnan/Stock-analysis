import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
from io import StringIO

# Set page configuration
st.set_page_config(
    page_title="Stock Data Visualization",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("Stock Data Visualization Tool")
st.write("""
This application fetches financial data from Yahoo Finance based on the stock symbol you provide.
You can view key financial metrics, analyze stock price trends, and download the data as a CSV file.
""")

# Sidebar with input elements
with st.sidebar:
    st.header("Input Parameters")
    
    # Symbol input with validation
    symbol = st.text_input("Enter Stock Symbol (e.g., AAPL, MSFT, GOOGL)", value="AAPL").upper()
    
    # Date range selection
    st.subheader("Select Date Range")
    today = datetime.now()
    
    # Default to 1 year of data
    default_start_date = today - timedelta(days=365)
    start_date = st.date_input("Start Date", value=default_start_date)
    end_date = st.date_input("End Date", value=today)
    
    # Period selection
    period_options = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
    period = st.selectbox("Or select a time period", period_options, index=5)
    
    # Interval selection
    interval_options = ["1d", "5d", "1wk", "1mo", "3mo"]
    interval = st.selectbox("Select interval", interval_options, index=0)

# Function to get stock data
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def get_stock_data(ticker, start=None, end=None, period=None, interval="1d"):
    try:
        if period and period != "custom":
            data = yf.download(ticker, period=period, interval=interval)
        else:
            data = yf.download(ticker, start=start, end=end, interval=interval)
        
        if data.empty:
            return None
        return data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# Function to get stock info
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def get_stock_info(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        return info
    except Exception as e:
        st.error(f"Error fetching stock info: {e}")
        return None

# Function to create a download link for dataframe
def get_csv_download_link(df, filename="stock_data.csv"):
    csv = df.to_csv(index=True)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV File</a>'
    return href

# Main content area
if st.sidebar.button("Fetch Stock Data"):
    if not symbol:
        st.error("Please enter a stock symbol")
    else:
        # Display loading message
        with st.spinner(f"Fetching data for {symbol}..."):
            # Get stock data
            if period != "custom":
                df = get_stock_data(symbol, period=period, interval=interval)
            else:
                df = get_stock_data(symbol, start=start_date, end=end_date, interval=interval)
            
            # Get stock info
            info = get_stock_info(symbol)
            
            if df is None or info is None:
                st.error(f"Could not retrieve data for {symbol}. Please verify the stock symbol and try again.")
            else:
                # Display company info
                st.header(f"{info.get('shortName', symbol)} ({symbol})")
                
                # Create columns for metrics
                col1, col2, col3, col4 = st.columns(4)
                
                try:
                    # Display key financial metrics
                    with col1:
                        st.metric("Current Price", f"${info.get('currentPrice', 'N/A'):.2f}")
                    
                    with col2:
                        st.metric("Market Cap", f"${info.get('marketCap', 0)/1_000_000_000:.2f}B")
                    
                    with col3:
                        st.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A'):.2f}")
                    
                    with col4:
                        st.metric("52W Range", f"${info.get('fiftyTwoWeekLow', 'N/A'):.2f} - ${info.get('fiftyTwoWeekHigh', 'N/A'):.2f}")
                except (TypeError, KeyError):
                    st.warning("Some financial metrics are not available for this stock")
                
                # Stock price chart
                st.subheader("Stock Price History")
                
                # Create a Plotly figure
                fig = go.Figure()
                
                fig.add_trace(go.Candlestick(
                    x=df.index,
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close'],
                    name='Candlestick'
                ))
                
                # Add volume as a bar chart on a secondary y-axis
                fig.add_trace(go.Bar(
                    x=df.index,
                    y=df['Volume'],
                    name='Volume',
                    marker_color='rgba(0, 0, 255, 0.3)',
                    yaxis='y2'
                ))
                
                # Update layout with secondary y-axis for volume
                fig.update_layout(
                    title=f"{symbol} Stock Price and Volume",
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    yaxis2=dict(
                        title="Volume",
                        overlaying="y",
                        side="right",
                        showgrid=False
                    ),
                    height=600,
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Additional metrics table
                st.subheader("Key Financial Metrics")
                
                # Create a dataframe of key metrics
                key_metrics = {}
                metric_keys = [
                    'previousClose', 'open', 'dayLow', 'dayHigh', 'volume', 'averageVolume',
                    'fiftyDayAverage', 'twoHundredDayAverage', 'marketCap', 'beta',
                    'trailingPE', 'forwardPE', 'dividendYield', 'trailingAnnualDividendYield',
                    'earningsQuarterlyGrowth', 'priceToSalesTrailing12Months'
                ]
                
                for key in metric_keys:
                    if key in info:
                        # Format the value appropriately
                        value = info[key]
                        if 'volume' in key.lower() or key == 'marketCap':
                            value = f"{value:,}"
                        elif 'yield' in key.lower() and value is not None:
                            value = f"{value:.2%}"
                        elif isinstance(value, (int, float)):
                            value = f"{value:.2f}"
                        key_metrics[key] = value
                
                # Create a DataFrame for display
                metrics_df = pd.DataFrame({
                    'Metric': list(key_metrics.keys()),
                    'Value': list(key_metrics.values())
                })
                
                # Rename the metrics for better readability
                name_mapping = {
                    'previousClose': 'Previous Close',
                    'open': 'Open',
                    'dayLow': 'Day Low',
                    'dayHigh': 'Day High',
                    'volume': 'Volume',
                    'averageVolume': 'Average Volume',
                    'fiftyDayAverage': '50-Day Average',
                    'twoHundredDayAverage': '200-Day Average',
                    'marketCap': 'Market Cap',
                    'beta': 'Beta',
                    'trailingPE': 'Trailing P/E',
                    'forwardPE': 'Forward P/E',
                    'dividendYield': 'Dividend Yield',
                    'trailingAnnualDividendYield': 'Trailing Annual Dividend Yield',
                    'earningsQuarterlyGrowth': 'Earnings Quarterly Growth',
                    'priceToSalesTrailing12Months': 'Price to Sales (TTM)'
                }
                
                metrics_df['Metric'] = metrics_df['Metric'].map(lambda x: name_mapping.get(x, x))
                
                # Display the metrics table
                st.table(metrics_df)
                
                # Historical data table with download option
                st.subheader("Historical Data")
                st.dataframe(df, use_container_width=True)
                
                # Download button for CSV
                st.markdown(get_csv_download_link(df, f"{symbol}_data.csv"), unsafe_allow_html=True)
                
                # Provide some additional information about the company
                if 'longBusinessSummary' in info:
                    with st.expander("About the Company"):
                        st.write(info['longBusinessSummary'])

# Provide instructions if no data has been fetched yet
if 'df' not in locals():
    st.info("Enter a stock symbol in the sidebar and click 'Fetch Stock Data' to begin.")
    
    # Display a sample of popular stocks
    st.subheader("Popular Stocks")
    popular_stocks = {
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation",
        "GOOGL": "Alphabet Inc.",
        "AMZN": "Amazon.com, Inc.",
        "TSLA": "Tesla, Inc.",
        "META": "Meta Platforms, Inc.",
        "NVDA": "NVIDIA Corporation",
        "JPM": "JPMorgan Chase & Co.",
        "V": "Visa Inc.",
        "WMT": "Walmart Inc."
    }
    
    # Create a dataframe of popular stocks
    popular_stocks_df = pd.DataFrame({
        "Symbol": list(popular_stocks.keys()),
        "Company Name": list(popular_stocks.values())
    })
    
    st.table(popular_stocks_df)

# Footer
st.markdown("---")
st.caption("Data provided by Yahoo Finance. This tool is for informational purposes only.")