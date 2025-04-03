import argparse
import csv
import os
import json
from bourstad.scraper import fetch_and_parse_stocks, fetch_stock_details, parse_all_stocks, fetch_enhanced_stock_data
from bourstad.analyzer import analyze_stocks

def main():
    parser = argparse.ArgumentParser(description='Bourstad Assistant Tool')
    parser.add_argument('--action', type=str, choices=['run_all', 'view_stocks', 'get_recommendations', 'help_actions'], required=True, help='Action to perform')
    args = parser.parse_args()

    if args.action == 'help_actions':
        print("Available actions:")
        print("1. run_all: Fetch, parse, and save detailed stock data.")
        print("2. view_stocks: Fetch and parse stock data to view available stocks.")
        print("3. get_recommendations: Analyze stocks and provide recommendations.")
        return

    if args.action == 'run_all':
        # Step 1: Fetch and parse stock data
        print("Fetching and parsing stock data...")
        stocks, suid, aut = fetch_and_parse_stocks()
        if not stocks:
            print("No stocks found. Exiting.")
            return

        # Step 2: Fetch detailed stock HTML files
        print("Fetching detailed stock HTML files...")
        fetch_stock_details()

        # Step 3: Parse detailed stock data
        print("Parsing detailed stock data...")
        parse_all_stocks('data/stocks')

        # Step 4: Fetch real-time stock data using yfinance
        print("Fetching real-time stock data...")
        symbols = [stock['id'] for stock in stocks]
        df = fetch_enhanced_stock_data(symbols)
        df.to_csv("data/real_time_stock_data.csv", index=False)
        print("Real-time stock data saved to data/real_time_stock_data.csv")

    elif args.action == 'view_stocks':
        # Step 1: Fetch and parse stock data
        print("Fetching and parsing stock data...")
        stocks, _, _ = fetch_and_parse_stocks()
        if stocks:
            print("Stocks fetched and parsed successfully!")
            for stock in stocks:
                print(f"Symbol: {stock['id']}, Name: {stock['name']}")
        else:
            print("No stocks found.")

    elif args.action == 'get_recommendations':
        # Load the extracted stock data
        print("Loading extracted stock data...")
        with open('detailed_stock_data.json', 'r', encoding='utf-8') as json_file:
            detailed_data = json.load(json_file)

        # Analyze the stocks
        print("Analyzing stocks...")
        recommendations = analyze_stocks(detailed_data)

        # Print recommendations
        for recommendation in recommendations:
            print(recommendation)

if __name__ == "__main__":
    main()