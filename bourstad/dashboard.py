import streamlit as st
import pandas as pd
import os
import json
import time
import yfinance as yf  # Add this import
from scraper import fetch_and_parse_stocks, fetch_owned_securities, fetch_with_cache, fetch_highlights_data, fetch_stock_data, fetch_batch_stock_data
from bs4 import BeautifulSoup
import requests

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Set the page configuration
st.set_page_config(page_title="Bourstad Assistant", page_icon="📈")

# Filter valid symbols
def filter_valid_symbols(symbols):
    # Use the centralized map_bourstad_to_yfinance function from scraper.py
    from scraper import map_bourstad_to_yfinance
    valid_symbols = []
    for symbol in symbols:
        mapped_symbol = map_bourstad_to_yfinance(symbol)
        if mapped_symbol:
            valid_symbols.append(mapped_symbol)
    return valid_symbols

# Fetch securities from Bourstad or load from a local file if login is not available
def get_bourstad_securities():
    """
    Fetch securities from Bourstad or load from a local file if login is not available.
    Returns:
        DataFrame: DataFrame containing stock data.
    """
    try:
        # Attempt to fetch stocks using login credentials
        email = os.getenv('BOURSTAD_USERNAME')
        password = os.getenv('BOURSTAD_PASSWORD')
        if email and password:
            stocks, _, _ = fetch_and_parse_stocks(email, password)
        else:
            raise ValueError("No login credentials provided. Falling back to local data.")

    except Exception as e:
        print(f"Error fetching stocks: {e}")
        # Fallback: Load stocks from a local file
        stocks = []
        extracted_stocks_file = "data/extracted_stocks.txt"
        if os.path.exists(extracted_stocks_file):
            with open(extracted_stocks_file, "r", encoding="utf-8") as file:
                for line in file:
                    parts = line.split(", ")
                    if len(parts) > 1 and "ID: " in parts[0]:
                        stock_id = parts[0].replace("ID: ", "").strip()
                        stock_name = parts[1].replace("Name: ", "").strip()
                        if stock_id:  # Skip empty or invalid symbols
                            stocks.append({"id": stock_id, "name": stock_name})
        else:
            print(f"Local stock data file '{extracted_stocks_file}' not found.")

    # Remove the 0th symbol (nonexistent)
    stocks = [stock for stock in stocks if stock['id'] and stock['id'] != ""]
    return pd.DataFrame(stocks)

# Generate a recommendation based on real-time data
def generate_recommendation(real_time_data):
    current_price = real_time_data.get("Current Price", "N/A")
    high_52_week = real_time_data.get("52-Week High", "N/A")
    low_52_week = real_time_data.get("52-Week Low", "N/A")

    # Ensure data is valid
    if current_price == "N/A" or high_52_week == "N/A" or low_52_week == "N/A":
        return "Neutral", 50  # Default to Neutral

    # Calculate recommendation based on proximity to 52-week high/low
    if current_price <= low_52_week * 1.1:
        return "Strong Buy", 100
    elif current_price <= low_52_week * 1.2:
        return "Buy", 75
    elif current_price >= high_52_week * 0.9:
        return "Strong Sell", 0
    elif current_price >= high_52_week * 0.8:
        return "Sell", 25
    else:
        return "Hold", 50

# Analyze stocks and generate recommendations
def analyze_stocks(stock_data):
    """
    Analyze all stocks and generate recommendations for non-owned securities.
    Args:
        stock_data (list): List of stock data with metrics.

    Returns:
        list: Recommendations for non-owned securities.
    """
    recommendations = []
    for stock in stock_data:
        # Safely access keys with default values
        symbol = stock.get("Symbol", "Unknown Symbol")
        name = stock.get("Name", "Unknown Name")
        current_price = stock.get("Current Price", 0)
        high_52_week = stock.get("52-Week High", 0)
        low_52_week = stock.get("52-Week Low", 0)
        pe_ratio = stock.get("P/E Ratio", 0)
        dividend_yield = stock.get("Dividend Yield", 0)

        # Ensure data is valid
        if current_price == 0 or high_52_week == 0 or low_52_week == 0:
            recommendations.append(f"{name} ({symbol}): Neutral - Insufficient data.")
            continue

        # Analyze proximity to 52-week highs/lows
        if current_price <= low_52_week * 1.1:
            recommendations.append(f"{name} ({symbol}): Strong Buy - Near 52-week low.")
        elif current_price <= low_52_week * 1.2:
            recommendations.append(f"{name} ({symbol}): Buy - Approaching 52-week low.")
        elif current_price >= high_52_week * 0.9:
            recommendations.append(f"{name} ({symbol}): Strong Sell - Near 52-week high.")
        elif current_price >= high_52_week * 0.8:
            recommendations.append(f"{name} ({symbol}): Sell - Approaching 52-week high.")
        else:
            recommendations.append(f"{name} ({symbol}): Hold - Trading within a stable range.")

        # Fundamental analysis
        if pe_ratio < 15 and dividend_yield > 0.03:
            recommendations.append(f"{name} ({symbol}): Buy - Strong fundamentals (Low P/E and High Dividend).")
        elif pe_ratio > 30:
            recommendations.append(f"{name} ({symbol}): Sell - Overvalued (High P/E).")

    return recommendations

# Analyze owned stocks and generate decisions
def analyze_owned_stocks(owned_securities, recommendations):
    decisions = []
    for owned in owned_securities:
        symbol = owned.get("Symbol", "N/A")
        recommendation = next((rec for rec in recommendations if symbol in rec), "Neutral")
        decisions.append(f"{owned['Name']} ({symbol}): {recommendation}")
    return decisions

def update_progress(current, total, message):
    """
    Update the progress bar and display a message.
    Args:
        current (int): Current progress count.
        total (int): Total progress count.
        message (str): Message to display alongside the progress bar.
    """
    progress_percentage = current / total
    progress_bar.progress(progress_percentage)
    progress_text.text(f"{message} ({current}/{total})")

def fetch_stock_details_with_progress(stocks, suid, aut):
    """
    Fetch stock details with a progress bar displayed on the dashboard.
    """
    base_url = "https://bourstad.cirano.qc.ca/Transaction/Transaction"
    os.makedirs('data/stocks', exist_ok=True)

    total_stocks = len(stocks)
    for index, stock in enumerate(stocks):
        symbol = stock['id']
        url = f"{base_url}?suid={suid}&aut={aut}&Symbol={symbol}"
        response = requests.get(url)
        if response.status_code == 200:
            with open(f"data/stocks/{symbol}.html", 'w', encoding='utf-8') as file:
                file.write(response.text)
        # Update the progress bar
        update_progress(index + 1, total_stocks, "Fetching stock details")

    st.success("Stock details fetched successfully!")

def parse_all_stocks_with_progress(directory):
    """
    Parse all stock files with a progress bar displayed on the dashboard.
    """
    stocks_dir = directory
    stock_files = [f for f in os.listdir(stocks_dir) if f.endswith('.html')]
    total_files = len(stock_files)

    all_stock_details = []
    for index, filename in enumerate(stock_files):
        filepath = os.path.join(stocks_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
            stock_details = {
                'symbol': filename.replace('.html', ''),
                'name': soup.find('h1', class_='stock-name').text.strip() if soup.find('h1', class_='stock-name') else 'N/A',
                'last_price': soup.find('span', class_='last-price').text.strip() if soup.find('span', class_='last-price') else 'N/A',
                'market_cap': soup.find('div', class_='market-cap').text.strip() if soup.find('div', class_='market-cap') else 'N/A',
            }
            all_stock_details.append(stock_details)
        # Update the progress bar
        update_progress(index + 1, total_files, "Parsing stock files")

    with open('detailed_stock_data.json', 'w', encoding='utf-8') as json_file:
        json.dump(all_stock_details, json_file, indent=4, ensure_ascii=False)

    st.success("Stock files parsed successfully!")

# Streamlit app
st.title("Bourstad Assistant 📊")
st.write("Welcome to the Bourstad Assistant! Use the tabs below to explore data and analysis.")

# Initialize a global progress bar
progress_bar = st.progress(0)  # Initialize the progress bar
progress_text = st.empty()  # Placeholder for progress text

# Sidebar for login
if 'suid' not in st.session_state or 'aut' not in st.session_state:
    with st.sidebar:
        st.header("Login")
        email = st.text_input("Email", type="default")
        password = st.text_input("Password", type="password")
        login_button = st.button("Login")

        if login_button:
            # Authenticate and fetch stocks
            with st.spinner("Logging in..."):
                stocks, suid, aut = fetch_and_parse_stocks(email, password)
                if suid and aut:
                    st.success("Login successful!")
                    st.session_state['suid'] = suid
                    st.session_state['aut'] = aut
                    st.session_state['stocks'] = stocks
                else:
                    st.error("Login failed. Please check your credentials.")
else:
    # Clear the sidebar after login
    st.sidebar.empty()

# Ensure stocks are loaded even without login
if 'stocks' not in st.session_state:
    st.session_state['stocks'] = get_bourstad_securities()

# Create tabs
tabs = st.tabs(["📈 Data", "🧠 Analysis", "📅 Highlights"])

# Tab 1: Data
with tabs[0]:
    st.header("All Securities")
    
    # Load securities data
    securities_df = pd.DataFrame(st.session_state['stocks'])
    securities_df = securities_df[securities_df['id'].notnull() & (securities_df['id'] != "")]

    # Display the filtered securities
    st.dataframe(securities_df)

    # Select a security to view details
    selected_security = st.selectbox("Select a security to view details", securities_df['id'])

    if selected_security:
        st.header(f"Real-Time Data for {selected_security}")
        real_time_data = fetch_stock_data(selected_security, securities_df)

        if not real_time_data:
            st.error(f"Failed to fetch real-time data for {selected_security}. Please try again later.")
        else:
            st.json(real_time_data)

            # Fetch historical data for the selected security
            time_period = st.selectbox("Select a time period for historical data", ["1d", "5d", "1mo", "6mo", "1y", "5y", "max"])
            stock = yf.Ticker(selected_security.split(":")[0])  # Extract the symbol for yfinance
            historical_data = stock.history(period=time_period)

            if historical_data.empty:
                st.warning("No historical data available for the selected time period.")
            else:
                # Display the graph
                st.subheader(f"Historical Price Chart for {selected_security} ({time_period})")
                st.line_chart(historical_data['Close'])

            # Add the recommendation slider with color gradient
            st.subheader("Recommendation Slider")
            recommendation, score = generate_recommendation(real_time_data)

            # Map recommendation score to slider position
            slider_position = {
                "Strong Buy": 100,
                "Buy": 75,
                "Hold": 50,
                "Sell": 25,
                "Strong Sell": 0
            }.get(recommendation, 50)  # Default to "Hold" if recommendation is unknown

            # Create a color gradient bar
            st.markdown(f"""
            <div style="width: 100%; height: 20px; background: linear-gradient(to right, red, orange, yellow, lightgreen, green); position: relative; border-radius: 5px;">
                <div style="position: absolute; left: {slider_position}%; top: -5px; transform: translateX(-50%);">
                    <span style="font-size: 16px; font-weight: bold; color: black;">&#x25B2;</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# Tab 2: Analysis
with tabs[1]:
    st.header("Stock Analysis")
    st.write("Analyze stocks and get recommendations for owned and non-owned securities.")

    # Fetch owned securities
    if 'suid' in st.session_state and 'aut' in st.session_state:
        owned_securities = fetch_owned_securities(st.session_state['suid'], st.session_state['aut'])
        if owned_securities:
            st.subheader("Owned Securities")
            owned_securities_df = pd.DataFrame(owned_securities)
            st.dataframe(owned_securities_df)

            # Analyze owned securities
            st.subheader("Owned Securities Decisions")

            # Generate recommendations for all stocks
            recommendations = analyze_stocks(st.session_state['stocks'])

            # Generate decisions for owned securities
            decisions = analyze_owned_stocks(owned_securities, recommendations)

            # Convert decisions into a DataFrame for better readability
            decisions_data = []
            for decision in decisions:
                # Parse the decision string into structured data
                symbol = decision.split("(")[1].split(")")[0]  # Extract symbol
                name = decision.split("(")[0].strip()  # Extract name
                recommendation = decision.split(":")[-1].strip()  # Extract recommendation
                decisions_data.append({"Symbol": symbol, "Name": name, "Decision": recommendation})

            # Display the decisions as a table
            decisions_df = pd.DataFrame(decisions_data)
            st.table(decisions_df)
        else:
            st.write("No owned securities found.")
    else:
        st.write("Please log in to view owned securities.")

    # Analyze and display 9 securities (3 low-risk, 3 moderate-risk, 3 high-risk)
    if 'stocks' in st.session_state:
        st.subheader("Top 9 Securities by Risk Category")

        # Fetch real-time data for all stocks
        stocks_df = pd.DataFrame(st.session_state['stocks'])
        valid_symbols = filter_valid_symbols(stocks_df['id'].tolist())
        if not valid_symbols:
            st.write("No valid symbols found.")
            st.stop()
        real_time_data = fetch_batch_stock_data(valid_symbols, stocks_df)

        print("Valid symbols:", valid_symbols)
        print("Real-time data fetched:", real_time_data)

        # Convert to DataFrame
        real_time_df = pd.DataFrame(real_time_data)
        print("Columns in real_time_df:", real_time_df.columns)

        # Ensure required columns exist in real_time_df
        required_columns = ["Dividend Yield", "P/E Ratio", "Current Price"]
        for column in required_columns:
            if column not in real_time_df.columns:
                real_time_df[column] = 0  # Default to 0 if missing

        print(real_time_df.head())

        # Categorize securities by risk
        low_risk = real_time_df[real_time_df['Dividend Yield'] > 0.03].sort_values(by='Current Price').head(3)
        moderate_risk = real_time_df[(real_time_df['P/E Ratio'] > 15) & (real_time_df['P/E Ratio'] <= 30)].sort_values(by='Current Price').head(3)
        high_risk = real_time_df[real_time_df['P/E Ratio'] > 30].sort_values(by='Current Price').head(3)

        # Combine the selected securities
        top_securities = pd.concat([low_risk, moderate_risk, high_risk])

        # Display the table
        st.dataframe(top_securities)

        # Analyze the selected securities
        st.subheader("Recommendations for Top Securities")
        for _, stock in top_securities.iterrows():
            recommendation = generate_recommendation(stock)
            st.write(f"{stock['Name']} ({stock['Symbol']}): {recommendation[0]} (Score: {recommendation[1]})")

# Tab 3: Highlights
with tabs[2]:
    st.header("📅 Highlights of the Day")
    st.write("View notable changes and honorable mentions for a specific day.")

    # Date picker for selecting a date
    selected_date = st.date_input("Select a date", value=pd.Timestamp.today())
    st.write(f"Showing highlights for: {selected_date}")

    # Fetch historical data for all valid symbols
    stocks_df = pd.DataFrame(st.session_state['stocks'])
    valid_symbols = filter_valid_symbols(stocks_df['id'].tolist())
    if not valid_symbols:
        st.write("No valid symbols found.")
        st.stop()

    highlights_df = fetch_highlights_data(valid_symbols, selected_date)
    if highlights_df is None or highlights_df.empty:
        st.write("No highlights data available for the selected date.")
    else:
        # Identify notable changes
        st.subheader("📈 Largest Gainers")
        gainers = highlights_df.sort_values(by="Change (%)", ascending=False).head(3)
        st.dataframe(gainers)

        st.subheader("📉 Largest Losers")
        losers = highlights_df.sort_values(by="Change (%)", ascending=True).head(3)
        st.dataframe(losers)

        st.subheader("🔥 Highest Volume")
        highest_volume = highlights_df.sort_values(by="Volume", ascending=False).head(3)
        st.dataframe(highest_volume)

        st.subheader("🎖️ Honorable Mentions")
        st.write("Stocks with notable performance or activity:")
        for _, row in highlights_df.iterrows():
            if abs(row["Change (%)"]) > 5 or row["Volume"] > 1_000_000:
                st.write(f"- {row['Name']} ({row['Symbol']}): {row['Change (%)']:.2f}% change, Volume: {row['Volume']}")

# Example usage of the progress bar functions
if st.button("Fetch and Parse Securities"):
    email = os.getenv('BOURSTAD_USERNAME')
    password = os.getenv('BOURSTAD_PASSWORD')
    stocks, suid, aut = fetch_and_parse_stocks(email, password)
    if stocks:
        fetch_stock_details_with_progress(stocks, suid, aut)
        parse_all_stocks_with_progress('data/stocks')
    else:
        st.error("No stocks found or failed to fetch stocks.")