# Bourstad-Helper 📈

Bourstad-Helper is a tool designed to assist users in analyzing and managing stocks from the Bourstad platform. It provides real-time stock data, historical price charts, and recommendations based on both fundamental and technical analysis.

---

## Features

- **Real-Time Stock Data**: Fetch and display current stock prices, market cap, 52-week high/low, and more.
- **Historical Price Charts**: Visualize stock performance over various time periods.
- **Stock Recommendations**: Get buy/sell recommendations based on fundamental and technical indicators.
- **Interactive Dashboard**: Explore data and analysis through a user-friendly Streamlit interface.
- **No Login Required**: View the "Data" and "Highlights" tabs without logging in.

---

## Setup

### Prerequisites

1. **Python**: Ensure you have Python 3.8 or higher installed.
2. **Dependencies**: Install the required Python libraries listed in `requirements.txt`.

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/Bourstad-Helper.git
   cd Bourstad-Helper
   ```

## How to Use

1. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the tool:

   ```bash
   python main.py --action view_stocks
   ```

3. Get recommendations:

   ```bash
   python main.py --action get_recommendations
   ```
