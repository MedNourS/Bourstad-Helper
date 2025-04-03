import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import os
import json
import yfinance as yf
import pandas as pd
import logging
from tqdm import tqdm  # Add this import for the progress bar

# Configure logging
LOG_FILE = "debug_log.txt"
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables from .env file
load_dotenv()

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_and_parse_stocks(email, password):
    """
    Authenticate with Bourstad and fetch available stocks.
    Args:
        email (str): User's email address.
        password (str): User's password.

    Returns:
        tuple: (list of stocks, suid, aut)
    """
    login_url = os.getenv('BOURSTAD_LOGIN_URL')
    stocks_url = os.getenv('BOURSTAD_STOCKS_URL')

    if not login_url or not stocks_url:
        print("Error: Missing URLs in environment variables.")
        logging.error("Missing URLs in environment variables.")
        return [], None, None

    session = requests.Session()
    login_page = session.get(login_url)
    soup = BeautifulSoup(login_page.content, 'html.parser')

    # Extract hidden fields from the login page
    hidden_fields = {hidden_input.get('name'): hidden_input.get('value', '') for hidden_input in soup.find_all('input', type='hidden')}
    credentials = {'txt_email': email, 'txt_password': password, **hidden_fields}

    # Perform login
    login_response = session.post(login_url, data=credentials, allow_redirects=True)
    if login_response.status_code != 200 or "Se connecter" in login_response.text:
        print("Login failed. Please check your email and password.")
        logging.error("Login failed. Please check your email and password.")
        return [], None, None

    # Extract suid and aut from the login response URL
    parsed_url = urlparse(login_response.url)
    suid = parse_qs(parsed_url.query).get('suid', [None])[0]
    aut = parse_qs(parsed_url.query).get('aut', [None])[0]

    if not suid or not aut:
        print("Error: Missing suid or aut in the login response.")
        logging.error("Missing suid or aut in the login response.")
        return [], None, None

    # Fetch available stocks
    stocks_url_with_params = f"{stocks_url}?suid={suid}&aut={aut}"
    response = session.get(stocks_url_with_params)
    if response.status_code != 200:
        print(f"Failed to retrieve the stock data. Status code: {response.status_code}")
        logging.error(f"Failed to retrieve the stock data. Status code: {response.status_code}")
        return [], None, None

    soup = BeautifulSoup(response.content, 'html.parser')
    select_element = soup.find('select', class_='select2_demo_3')
    stocks = [{'id': option.get('id'), 'name': option.text.strip()} for option in select_element.find_all('option')] if select_element else []

    # Save stocks to a file
    os.makedirs('data', exist_ok=True)
    with open('data/extracted_stocks.txt', 'w', encoding='utf-8') as file:
        for stock in stocks:
            file.write(f"ID: {stock['id']}, Name: {stock['name']}\n")

    logging.info(f"Fetched stocks: {stocks}")
    return stocks, suid, aut

def fetch_stock_details():
    email = os.getenv('BOURSTAD_USERNAME')
    password = os.getenv('BOURSTAD_PASSWORD')
    stocks, suid, aut = fetch_and_parse_stocks(email, password)
    if not stocks:
        print("No stocks found to fetch details.")
        logging.warning("No stocks found to fetch details.")
        return

    base_url = "https://bourstad.cirano.qc.ca/Transaction/Transaction"
    os.makedirs('data/stocks', exist_ok=True)

    # Add a progress bar for fetching stock details
    for stock in tqdm(stocks, desc="Fetching stock details", unit="stock"):
        symbol = stock['id']
        url = f"{base_url}?suid={suid}&aut={aut}&Symbol={symbol}"
        response = requests.get(url)
        if response.status_code == 200:
            with open(f"data/stocks/{symbol}.html", 'w', encoding='utf-8') as file:
                file.write(response.text)
            logging.info(f"Fetched stock details for {symbol}.")
        else:
            logging.error(f"Failed to fetch stock details for {symbol}. Status code: {response.status_code}")

def parse_all_stocks(directory):
    stocks_dir = directory
    all_stock_details = []

    # List all HTML files and initialize a progress bar
    stock_files = [f for f in os.listdir(stocks_dir) if f.endswith('.html')]
    for filename in tqdm(stock_files, desc="Parsing stock files", unit="file"):
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

    with open('detailed_stock_data.json', 'w', encoding='utf-8') as json_file:
        json.dump(all_stock_details, json_file, indent=4, ensure_ascii=False)
    logging.info(f"Parsed all stocks and saved to detailed_stock_data.json.")

def fetch_enhanced_stock_data(symbols):
    stock_data = []
    invalid_symbols = []

    for symbol in symbols:
        try:
            # Reformat symbol if necessary (e.g., remove ":CA" or ":EGX")
            formatted_symbol = symbol.split(":")[0] if ":" in symbol else symbol

            stock = yf.Ticker(formatted_symbol)
            info = stock.info

            # Check if timezone metadata exists
            if not info.get("exchangeTimezoneName"):
                print(f"{symbol}: No timezone found; possibly delisted.")
                logging.warning(f"{symbol}: No timezone found; possibly delisted.")
                invalid_symbols.append(symbol)
                continue

            # Ensure the data is valid
            if "currentPrice" not in info or info["currentPrice"] is None:
                print(f"{symbol}: No data found; possibly delisted.")
                logging.warning(f"{symbol}: No data found; possibly delisted.")
                invalid_symbols.append(symbol)
                continue

            stock_data.append({
                "Symbol": symbol,
                "Name": info.get("longName", "N/A"),
                "Current Price": info.get("currentPrice", "N/A"),
                "Market Cap": info.get("marketCap", "N/A"),
                "P/E Ratio": info.get("trailingPE", "N/A"),
                "EPS": info.get("trailingEps", "N/A"),
                "Dividend Yield": info.get("dividendYield", "N/A"),
                "52-Week High": info.get("fiftyTwoWeekHigh", "N/A"),
                "52-Week Low": info.get("fiftyTwoWeekLow", "N/A"),
                "Volume": info.get("volume", "N/A"),
            })
            logging.info(f"Fetched enhanced stock data for {symbol}: {stock_data[-1]}")
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            logging.error(f"Error fetching data for {symbol}: {e}")
            invalid_symbols.append(symbol)

    # Log invalid symbols
    if invalid_symbols:
        print("\nThe following symbols could not be fetched:")
        for invalid_symbol in invalid_symbols:
            print(f"- {invalid_symbol}")
        logging.warning(f"The following symbols could not be fetched: {invalid_symbols}")

    return pd.DataFrame(stock_data)

def fetch_owned_securities(suid, aut):
    """
    Fetch the securities currently owned by the user from Bourstad.
    Args:
        suid (str): Session user ID.
        aut (str): Authentication token.

    Returns:
        list: A list of owned securities with details.
    """
    base_url = "https://bourstad.cirano.qc.ca/dashboard_Part/dashboard_Part"
    url = f"{base_url}?suid={suid}&aut={aut}"

    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch owned securities. Status code: {response.status_code}")
            logging.error(f"Failed to fetch owned securities. Status code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')

        # Parse the owned securities table
        table = soup.find('table', {'id': 'editable2'})
        if not table:
            print("No owned securities table found.")
            logging.warning("No owned securities table found.")
            return []

        owned_securities = []
        rows = table.find('tbody').find_all('tr')
        for row in rows:
            columns = row.find_all('td')
            if len(columns) < 5:
                continue  # Skip rows with missing data

            try:
                owned_securities.append({
                    "Symbol": columns[0].text.strip(),
                    "Name": columns[1].text.strip(),
                    "Quantity": int(columns[2].text.strip()),
                    "Average Price": float(columns[3].text.strip().replace('$', '').replace(',', '')),
                    "Current Price": float(columns[4].text.strip().replace('$', '').replace(',', '')),
                    "Gains and Losses": columns[5].text.strip(),
                })
                logging.info(f"Parsed owned security: {owned_securities[-1]}")
            except Exception as e:
                print(f"Error parsing row: {e}")
                logging.error(f"Error parsing row: {e}")

        return owned_securities

    except Exception as e:
        print(f"Error fetching owned securities: {e}")
        logging.error(f"Error fetching owned securities: {e}")
        return []

def fetch_with_cache(symbol):
    """
    Fetch stock data with caching.
    """
    cache_file = os.path.join(CACHE_DIR, f"{symbol}.json")

    # Check if data is already cached
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as file:
                data = json.load(file)
                logging.info(f"Cache hit for {symbol}: {data}")
                return data
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"Corrupted cache file detected for {symbol}: {e}")
            os.remove(cache_file)  # Delete the corrupted cache file

    # Fetch data from Yahoo Finance
    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        # Ensure the fetched data is valid
        if not info or not isinstance(info, dict):
            logging.warning(f"No valid data fetched for {symbol}.")
            return None

        # Cache the data
        with open(cache_file, "w") as file:
            json.dump(info, file)
        logging.info(f"Fetched and cached data for {symbol}: {info}")

        return info
    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {e}")
        return None

def fetch_highlights_data(symbols, selected_date):
    """
    Fetch and cache highlights data for a specific day.
    """
    try:
        cache_file = os.path.join(CACHE_DIR, f"highlights_{selected_date.strftime('%Y-%m-%d')}.json")

        # Check if data is already cached
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as file:
                    data = pd.DataFrame(json.load(file))
                    logging.info(f"Cache hit for highlights on {selected_date}: {data}")
                    return data
            except (json.JSONDecodeError, ValueError) as e:
                logging.error(f"Corrupted cache file detected for highlights on {selected_date}: {e}")
                os.remove(cache_file)  # Delete the corrupted cache file

        # Fetch historical data for all symbols
        historical_data = []
        for symbol in symbols:
            try:
                formatted_symbol = map_bourstad_to_yfinance(symbol)
                stock = yf.Ticker(formatted_symbol)

                # Check if timezone metadata exists
                if not stock.info.get("exchangeTimezoneName"):
                    logging.warning(f"{symbol}: No timezone found; possibly delisted.")
                    continue

                history = stock.history(start=selected_date, end=selected_date + pd.Timedelta(days=1))
                if history.empty:
                    logging.warning(f"{symbol}: No data found; possibly delisted.")
                    continue

                row = {
                    "Symbol": symbol,
                    "Name": stock.info.get("longName", "N/A"),
                    "Change (%)": ((history['Close'].iloc[-1] - history['Open'].iloc[0]) / history['Open'].iloc[0]) * 100,
                    "Volume": history['Volume'].iloc[-1],
                }
                historical_data.append(row)
                logging.info(f"Fetched historical data for {symbol}: {row}")
            except Exception as e:
                logging.error(f"Error fetching historical data for {symbol}: {e}")

        # Cache the data
        if historical_data:
            with open(cache_file, "w") as file:
                json.dump(historical_data, file)
            logging.info(f"Cached highlights data for {selected_date}: {historical_data}")

        return pd.DataFrame(historical_data)
    except Exception as e:
        logging.error(f"Error in fetch_highlights_data: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on failure

def fetch_stock_data(symbol, stocks_df):
    """
    Fetch real-time stock data with caching.
    """
    try:
        formatted_symbol = map_bourstad_to_yfinance(symbol)
        if not formatted_symbol:
            logging.warning(f"Invalid symbol mapping for {symbol}. Skipping.")
            return None

        info = fetch_with_cache(formatted_symbol)
        if not info or "currentPrice" not in info or info["currentPrice"] is None:
            logging.warning(f"No valid data for {formatted_symbol}. Skipping.")
            return None

        stock_data = {
            "Symbol": symbol,
            "Name": info.get("longName", "N/A"),
            "Current Price": info.get("currentPrice", "N/A"),
            "Market Cap": info.get("marketCap", "N/A"),
            "52-Week High": info.get("fiftyTwoWeekHigh", "N/A"),
            "52-Week Low": info.get("fiftyTwoWeekLow", "N/A"),
        }
        logging.info(f"Fetched stock data for {symbol}: {stock_data}")
        return stock_data
    except Exception as e:
        logging.error(f"Error fetching stock data for {symbol}: {e}")
        return None

def fetch_batch_stock_data(symbols, stocks_df, delay=0.05):
    """
    Fetch real-time stock data for a batch of symbols.
    """
    # ...existing code...

def map_bourstad_to_yfinance(bourstad_symbol):
    """
    Map Bourstad symbol to Yahoo Finance symbol.
    """
    # Add specific mappings for known symbols
    mappings = {
        "MMM:EGX": "MMM",  # Example mapping
        "VNP:CA": "VNP.TO",  # Example mapping for Canadian stocks
        # Add more mappings as needed
    }
    return mappings.get(bourstad_symbol, bourstad_symbol)  # Default to the same symbol

def output_security_mappings(email, password):
    """
    Fetch all securities and output their Bourstad and Yahoo Finance mappings to a JSON file.
    """
    stocks, _, _ = fetch_and_parse_stocks(email, password)
    if not stocks:
        print("No stocks found to map.")
        logging.warning("No stocks found to map.")
        return

    mappings = []
    for stock in stocks:
        bourstad_symbol = stock['id']
        yfinance_symbol = map_bourstad_to_yfinance(bourstad_symbol)
        mappings.append({
            "Bourstad Symbol": bourstad_symbol,
            "Yahoo Finance Symbol": yfinance_symbol,
            "Name": stock['name']
        })

    # Save mappings to a JSON file
    os.makedirs('data', exist_ok=True)
    output_file = os.path.join('data', 'security_mappings.json')
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(mappings, file, indent=4)
    logging.info(f"Security mappings saved to {output_file}")
    print(f"Security mappings saved to {output_file}")

if __name__ == "__main__":
    email = os.getenv('BOURSTAD_USERNAME')
    password = os.getenv('BOURSTAD_PASSWORD')

    # Output security mappings before anything else
    output_security_mappings(email, password)

    _, suid, aut = fetch_and_parse_stocks(email, password)
    print(f"suid: {suid}, aut: {aut}")
    logging.info(f"suid: {suid}, aut: {aut}")
    if suid and aut:
        fetch_owned_securities(suid, aut)
    else:
        print("Failed to retrieve suid and aut")
        logging.error("Failed to retrieve suid and aut")