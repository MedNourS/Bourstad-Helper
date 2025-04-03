import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import os
import json
import yfinance as yf
import pandas as pd

# Load environment variables from .env file
load_dotenv()

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
        return [], None, None

    # Extract suid and aut from the login response URL
    parsed_url = urlparse(login_response.url)
    suid = parse_qs(parsed_url.query).get('suid', [None])[0]
    aut = parse_qs(parsed_url.query).get('aut', [None])[0]

    if not suid or not aut:
        print("Error: Missing suid or aut in the login response.")
        return [], None, None

    # Fetch available stocks
    stocks_url_with_params = f"{stocks_url}?suid={suid}&aut={aut}"
    response = session.get(stocks_url_with_params)
    if response.status_code != 200:
        print(f"Failed to retrieve the stock data. Status code: {response.status_code}")
        return [], None, None

    soup = BeautifulSoup(response.content, 'html.parser')
    select_element = soup.find('select', class_='select2_demo_3')
    stocks = [{'id': option.get('id'), 'name': option.text.strip()} for option in select_element.find_all('option')] if select_element else []

    # Save stocks to a file
    os.makedirs('data', exist_ok=True)
    with open('data/extracted_stocks.txt', 'w', encoding='utf-8') as file:
        for stock in stocks:
            file.write(f"ID: {stock['id']}, Name: {stock['name']}\n")

    return stocks, suid, aut

def fetch_stock_details():
    email = os.getenv('BOURSTAD_USERNAME')
    password = os.getenv('BOURSTAD_PASSWORD')
    stocks, suid, aut = fetch_and_parse_stocks(email, password)
    if not stocks:
        print("No stocks found to fetch details.")
        return

    base_url = "https://bourstad.cirano.qc.ca/Transaction/Transaction"
    os.makedirs('data/stocks', exist_ok=True)

    for stock in stocks:
        symbol = stock['id']
        url = f"{base_url}?suid={suid}&aut={aut}&Symbol={symbol}"
        response = requests.get(url)
        if response.status_code == 200:
            with open(f"data/stocks/{symbol}.html", 'w', encoding='utf-8') as file:
                file.write(response.text)

def parse_all_stocks(directory):
    stocks_dir = directory
    all_stock_details = []

    for filename in os.listdir(stocks_dir):
        if filename.endswith('.html'):
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

def fetch_enhanced_stock_data(symbols):
    stock_data = []
    invalid_symbols = []

    for symbol in symbols:
        try:
            # Reformat symbol if necessary (e.g., remove ":CA" or ":EGX")
            formatted_symbol = symbol.split(":")[0] if ":" in symbol else symbol

            stock = yf.Ticker(formatted_symbol)
            info = stock.info

            # Ensure the data is valid
            if "currentPrice" not in info or info["currentPrice"] is None:
                raise ValueError(f"No valid data for {formatted_symbol}")

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
        except Exception as e:
            print(f"Failed to fetch data for {symbol}: {e}")
            invalid_symbols.append(symbol)

    # Log invalid symbols
    if invalid_symbols:
        print("\nThe following symbols could not be fetched:")
        for invalid_symbol in invalid_symbols:
            print(f"- {invalid_symbol}")

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
            return []

        soup = BeautifulSoup(response.content, 'html.parser')

        # Parse the owned securities table
        table = soup.find('table', {'id': 'editable2'})
        if not table:
            print("No owned securities table found.")
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
            except Exception as e:
                print(f"Error parsing row: {e}")

        return owned_securities

    except Exception as e:
        print(f"Error fetching owned securities: {e}")
        return []

if __name__ == "__main__":
    email = os.getenv('BOURSTAD_USERNAME')
    password = os.getenv('BOURSTAD_PASSWORD')
    _, suid, aut = fetch_and_parse_stocks(email, password)
    print(f"suid: {suid}, aut: {aut}")
    if suid and aut:
        fetch_owned_securities(suid, aut)
    else:
        print("Failed to retrieve suid and aut")