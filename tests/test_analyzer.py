import unittest
import os
from bourstad.analyzer import analyze_stocks
from bourstad.scraper import fetch_enhanced_stock_data

class TestAnalyzer(unittest.TestCase):
    def test_analyze_stocks(self):
        # Simulated stock data
        stocks = [
            {
                'Symbol': 'AAPL',
                'Name': 'Apple Inc.',
                'P/E Ratio': 15,
                'Dividend Yield': 0.03,
                'RSI': 25,  # Oversold
                'Initial Price': 150,
                'Final Price': 170,  # Price increased
            },
            {
                'Symbol': 'MSFT',
                'Name': 'Microsoft Corp.',
                'P/E Ratio': 35,
                'Dividend Yield': 0.01,
                'RSI': 75,  # Overbought
                'Initial Price': 300,
                'Final Price': 280,  # Price decreased
            },
            {
                'Symbol': 'GOOGL',
                'Name': 'Alphabet Inc.',
                'P/E Ratio': 25,
                'Dividend Yield': 0.00,
                'RSI': 50,  # Neutral
                'Initial Price': 2800,
                'Final Price': 2800,  # No change
            },
        ]

        # Run the analysis
        recommendations = analyze_stocks(stocks)

        # Assertions
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)

        # Check specific recommendations
        self.assertIn("Buy AAPL (Apple Inc.): Strong fundamentals.", recommendations)
        self.assertIn("Buy AAPL (Apple Inc.): Oversold (RSI < 30).", recommendations)
        self.assertIn("Sell MSFT (Microsoft Corp.): Overvalued.", recommendations)
        self.assertIn("Sell MSFT (Microsoft Corp.): Overbought (RSI > 70).", recommendations)
        self.assertNotIn("Buy GOOGL (Alphabet Inc.):", recommendations)
        self.assertNotIn("Sell GOOGL (Alphabet Inc.):", recommendations)

        # Evaluate accuracy
        correct_predictions = 0
        total_predictions = 0

        for stock in stocks:
            symbol = stock['Symbol']
            initial_price = stock['Initial Price']
            final_price = stock['Final Price']

            for recommendation in recommendations:
                if symbol in recommendation:
                    if "Buy" in recommendation and final_price > initial_price:
                        correct_predictions += 1
                    elif "Sell" in recommendation and final_price < initial_price:
                        correct_predictions += 1
                    total_predictions += 1

        # Calculate accuracy
        accuracy = (correct_predictions / total_predictions) * 100 if total_predictions > 0 else 0
        print(f"Accuracy: {accuracy}%")

        # Assert accuracy is reasonable (e.g., above 50%)
        self.assertGreaterEqual(accuracy, 50)

    def test_analyze_stocks_with_full_data(self):
        # Load stock symbols from extracted_stocks.txt
        extracted_stocks_file = "data/extracted_stocks.txt"
        if not os.path.exists(extracted_stocks_file):
            self.fail(f"{extracted_stocks_file} not found. Ensure the data is extracted.")

        symbols = []
        with open(extracted_stocks_file, "r", encoding="utf-8") as file:
            for line in file:
                parts = line.split(", ")
                if len(parts) > 0 and "ID: " in parts[0]:
                    symbol = parts[0].replace("ID: ", "").strip()
                    if symbol:  # Skip empty or invalid symbols
                        symbols.append(symbol)

        # Fetch real-time data for all symbols
        stock_data = fetch_enhanced_stock_data(symbols)

        # Ensure we have data to analyze
        self.assertGreater(len(stock_data), 0, "No stock data fetched for analysis.")

        # Run the analysis
        recommendations = analyze_stocks(stock_data.to_dict(orient="records"))

        # Ensure recommendations are generated
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0, "No recommendations generated.")

        # Print recommendations for manual inspection
        print("\nGenerated Recommendations:")
        for recommendation in recommendations:
            print(f"- {recommendation}")

if __name__ == '__main__':
    unittest.main()