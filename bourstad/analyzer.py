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
        symbol = stock.get("Symbol", "N/A")
        name = stock.get("Name", "N/A")
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


def analyze_owned_stocks(owned_securities, recommendations):
    """
    Analyze owned stocks and decide whether to buy more, sell, or hold.
    Args:
        owned_securities (list): List of owned securities with details.
        recommendations (list): Recommendations for all stocks.

    Returns:
        list: Decisions for owned securities.
    """
    decisions = []
    for owned in owned_securities:
        symbol = owned.get("Symbol", "N/A")
        name = owned.get("Name", "N/A")
        quantity = owned.get("Quantity", 0)
        average_price = owned.get("Average Price", 0)
        current_price = owned.get("Current Price", 0)
        gains_losses = owned.get("Gains and Losses", "N/A")

        # Ensure data is valid
        if current_price == 0 or average_price == 0:
            decisions.append(f"{name} ({symbol}): Hold - Insufficient data.")
            continue

        # Analyze gains/losses
        if "success" in gains_losses.lower():
            decisions.append(f"{name} ({symbol}): Hold - Positive gains ({gains_losses}).")
        elif "danger" in gains_losses.lower():
            decisions.append(f"{name} ({symbol}): Consider selling - Negative gains ({gains_losses}).")

        # Compare current price to average price
        if current_price > average_price * 1.2:
            decisions.append(f"{name} ({symbol}): Sell - Current price is significantly higher than average price.")
        elif current_price < average_price * 0.8:
            decisions.append(f"{name} ({symbol}): Buy more - Current price is significantly lower than average price.")
        else:
            decisions.append(f"{name} ({symbol}): Hold - Current price is close to average price.")

        # Incorporate general recommendations
        recommendation = next((rec for rec in recommendations if symbol in rec), None)
        if recommendation:
            decisions.append(f"{name} ({symbol}): {recommendation}")

    return decisions