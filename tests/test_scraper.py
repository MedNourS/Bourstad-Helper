from unittest.mock import patch, MagicMock
import unittest
from bourstad.scraper import fetch_current_stocks

class TestScraper(unittest.TestCase):
    @patch('bourstad.scraper.requests.Session')
    def test_fetch_current_stocks(self, MockSession):
        mock_session = MockSession.return_value
        mock_session.post.return_value.status_code = 200
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.content = b'[{"symbol": "AAPL", "price": 150.00, "volume": 1000}]'

        stocks = fetch_current_stocks()
        self.assertIsInstance(stocks, list)
        self.assertEqual(len(stocks), 1)
        self.assertEqual(stocks[0]['symbol'], 'AAPL')

    @patch('bourstad.scraper.requests.Session')
    def test_fetch_current_stocks_html(self, MockSession):
        mock_session = MockSession.return_value
        mock_session.post.return_value.status_code = 200
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.content = b"""
        <ul id="select2-ddl_symbols-vd-results">
            <li id="select2-ddl_symbols-vd-result-jd74-MMM:EGX" class="select2-results__option">3M Corp.</li>
            <li id="select2-ddl_symbols-vd-result-nj9j-VNP:CA" class="select2-results__option">5N Plus</li>
        </ul>
        """
        stocks = fetch_current_stocks()
        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0]['symbol'], 'MMM:EGX')
        self.assertEqual(stocks[0]['name'], '3M Corp.')

    @patch('bourstad.scraper.requests.Session')
    def test_fetch_current_stocks_invalid_login(self, MockSession):
        mock_session = MockSession.return_value
        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.text = "Invalid credentials"

        stocks = fetch_current_stocks()
        self.assertEqual(stocks, [])  # Expect an empty list on login failure

    @patch('bourstad.scraper.requests.Session')
    def test_fetch_current_stocks_empty_list(self, MockSession):
        mock_session = MockSession.return_value
        mock_session.post.return_value.status_code = 200
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.content = b'<ul id="select2-ddl_symbols-vd-results"></ul>'

        stocks = fetch_current_stocks()
        self.assertEqual(stocks, [])  # Expect an empty list if no stocks are found

if __name__ == '__main__':
    unittest.main()