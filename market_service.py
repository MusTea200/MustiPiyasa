import yfinance as yf
import logging

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_market_data(ticker_symbol: str):
    """
    Fetches current market data for a given ticker symbol using yfinance.
    
    Args:
        ticker_symbol (str): The ticker symbol (e.g., 'THYAO.IS', 'GC=F', 'AAPL').
        
    Returns:
        dict: A dictionary containing price information or None if failed.
    """
    try:
        # Normalize symbol for BIST if needed (User might say THYAO, we need THYAO.IS)
        # Simple heuristic: if it's likely a BIST stock and no suffix key, add .IS
        # But for now, let's trust the AI or user to provide correct suffix or handle commonly known ones.
        
        # Common Turkish stocks mapping if user forgets .IS
        # This is a basic helper list
        common_tr_stocks = ["THYAO", "GARAN", "AKBNK", "ASELS", "KCHOL", "BIMAS", "EREGL", "SISE", "TUPRS"]
        
        clean_symbol = ticker_symbol.upper().strip()
        if clean_symbol in common_tr_stocks:
            clean_symbol += ".IS"
            
        # Altın/Dolar adjustments for common names
        if clean_symbol == "ALTIN" or clean_symbol == "GOLD":
            clean_symbol = "GC=F" # Gold Futures
        elif clean_symbol in ["DOLAR", "USD", "USDTRY"]:
            clean_symbol = "TRY=X" # USD/TRY exchange rate
        elif clean_symbol in ["EURO", "EUR", "EURTRY"]:
            clean_symbol = "EURTRY=X"
            
        ticker = yf.Ticker(clean_symbol)
        
        # Get fast info first (often faster and sufficient for current price)
        # fast_info is a dictionary-like object
        
        current_price = None
        previous_close = None
        currency = "USD"
        
        # Try fetching via fast_info (newer yfinance)
        if hasattr(ticker, 'fast_info'):
            try:
                current_price = ticker.fast_info['lastPrice']
                previous_close = ticker.fast_info['previousClose']
                currency = ticker.fast_info['currency']
            except:
                pass
                
        # Fallback to history if fast_info fails
        if current_price is None:
            hist = ticker.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                # Try to get info for currency
                try:
                    currency = ticker.info.get('currency', '?')
                    previous_close = ticker.info.get('previousClose', current_price)
                except:
                    pass
            else:
                logger.error(f"No data found for symbol: {clean_symbol}")
                return None

        change = 0.0
        change_percent = 0.0
        
        if previous_close and previous_close > 0:
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100

        return {
            "symbol": clean_symbol,
            "price": round(current_price, 2),
            "currency": currency,
            "change": round(change, 2),
            "change_percent": round(change_percent, 2)
        }

    except Exception as e:
        logger.error(f"Error fetching data for {ticker_symbol}: {e}")
        return None

if __name__ == "__main__":
    # Test
    print(get_market_data("THYAO"))
    print(get_market_data("USD"))
    print(get_market_data("ALTIN"))
