import os
import sys
import warnings
# Suppress specific legacy warning from google.generativeai
warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from dotenv import load_dotenv
from market_service import get_market_data
from notification_service import add_alert, add_time_alert, update_balance, get_portfolio_status, get_active_alerts, delete_alert

# Load environment variables
load_dotenv()

class MarketAIAgent:
    def __init__(self, user_id=None):
        """
        Initializes the AI agent.
        user_id is optional but required for setting alerts effectively via tools.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        self.user_id = user_id
        genai.configure(api_key=api_key)
        
        # Define wrapper for add_alert that doesn't require user_id argument (inject it)
        def create_alert(symbol: str, target_price: float, condition: str):
            """
            Creates a price alert for a given symbol.
            
            Args:
                symbol (str): The stock/market symbol (e.g. 'THYAO', 'USD', 'ALTIN').
                target_price (float): The target price value.
                condition (str): The condition, must be either 'above' (yukarı/üzerinde) or 'below' (aşağı/altında).
            """
            if not self.user_id:
                return "Hata: Alarm kurmak için kullanıcı kimliği (user_id) tanımlanamadı."
            
            # Basic normalization (AI usually handles this well, but let's be safe)
            cond = condition.lower()
            if 'above' in cond or 'yukarı' in cond or 'üzeri' in cond or 'fazla' in cond:
                cond = 'above'
            elif 'below' in cond or 'aşağı' in cond or 'altı' in cond or 'düşük' in cond:
                cond = 'below'
            
            # Map common names to symbols if needed (though market_service does some too)
            # The AI might pass 'Altın' directly, so we rely on market_service or just pass it clearly.
            # Best practice: Explain in system instruction for model to use clean symbols, but here we just pass it.
            
            result = add_alert(symbol, target_price, cond, self.user_id)
            return result

        def create_timer(seconds: int, note: str = ""):
            """
            Creates a time-based alert (timer).
            
            Args:
                seconds (int): How many seconds later to alert. (e.g. 60 for 1 minute).
                note (str): Optional note to remind.
            """
            if not self.user_id:
                return "Hata: Kullanıcı kimliği yok."
            
            result = add_time_alert(seconds, self.user_id, note)
            return result

        def update_balance_tool(symbol: str, amount: float, unit: str):
            """
            Updates the user's asset balance.
            Args:
                symbol (str): Asset symbol (e.g. ALTIN, THYAO, USD).
                amount (float): Quantity.
                unit (str): Unit (e.g. gram, lot, adet).
            """
            if not self.user_id:
                return "Hata: Kullanıcı ID yok."
            return update_balance(self.user_id, symbol, amount, unit)

        def get_portfolio_tool():
            """
            Returns the current status and total value of the user's portfolio.
            """
            if not self.user_id:
                return "Hata: Kullanıcı ID yok."
            return get_portfolio_status(self.user_id)

        def list_alerts_tool():
            """
            Lists all active alerts for the user.
            """
            if not self.user_id:
                return "Hata: Kullanıcı ID yok."
            return get_active_alerts(self.user_id)

        def cancel_alert_tool(index: int):
            """
            Cancels an alert by its list number.
            Args:
                index (int): The number of the alert to cancel (e.g. 1, 2).
            """
            print(f"DEBUG: cancel_alert_tool called with index: {index}")
            if not self.user_id:
                return "Hata: Kullanıcı ID yok."
            # Ensure int
            try:
                idx = int(index)
            except:
                return "Lütfen geçerli bir sayı belirtin."
            return delete_alert(self.user_id, idx)

        # Tools available to the model
        self.tools = [get_market_data, create_alert, create_timer, update_balance_tool, get_portfolio_tool, list_alerts_tool, cancel_alert_tool]
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash', 
            tools=self.tools,
            system_instruction=(
                "Sen yardımcı bir piyasa asistanısın. Kullanıcı piyasa verilerini sorabilir, alarm kurabilir veya bakiyesini yönetebilir.\n"
                "- Bakiye güncellemek için: update_balance_tool (Örn: '500 gr altınım var')\n"
                "- Portföy durumu için: get_portfolio_tool (Örn: 'Durumum nedir?')\n"
                "- Aktif alarmları görmek için: list_alerts_tool (Örn: 'Alarmlarımı listele')\n"
                "- Alarm iptal etmek için: cancel_alert_tool (Örn: '1. alarmı sil')\n"
                "- Fiyat alarmı için: create_alert\n"
                "- Süre alarmı için: create_timer\n"
                "- Fiyat sorgusu için: get_market_data\n"
                "Sembolleri ve birimleri doğru anla. Yanıtların Türkçe olsun."
            )
        )
        
        # Start a chat session
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)

    def send_message(self, user_message):
        """
        Sends a message to Gemini and returns the response.
        Handles automatic function calling via the library if enabled,
        or we can handle it manually if we want more control. 
        Note: enabled_automatic_function_calling=True handles the tool loop automatically.
        """
        try:
            response = self.chat.send_message(user_message)
            return response.text
        except Exception as e:
            return f"Bir hata oluştu: {str(e)}"

if __name__ == "__main__":
    # Test
    sys.stdout.reconfigure(encoding='utf-8')
    # Note: This will fail if GEMINI_API_KEY is not set in .env
    try:
        # Mock user ID for test
        agent = MarketAIAgent(user_id=12345)
        print("User: THYAO ne kadar?")
        response = agent.send_message("THYAO ne kadar?")
        print(f"Gemini: {response}")
        
        print("\nUser: Dolar 50 olunca haber ver.")
        response = agent.send_message("Dolar 50 olunca haber ver.")
        print(f"Gemini: {response}")

        print("\nUser: 5 saniye sonra test diye hatırlat.")
        response = agent.send_message("5 saniye sonra test diye hatırlat.")
        print(f"Gemini: {response}")

        print("\nUser: 540 gram altınım var.")
        response = agent.send_message("540 gram altınım var.")
        print(f"Gemini: {response}")

        print("\nUser: Durumum nedir?")
        response = agent.send_message("Durumum nedir?")
        print(f"Gemini: {response}")

        print("\nUser: Alarmlarımı listele.")
        response = agent.send_message("Alarmlarımı listele.")
        print(f"Gemini: {response}")

        print("\nUser: 1. alarmı ve 2. alarmı sil.") 
        # Note: Gemini might try to call tool twice or answer textually.
        response = agent.send_message("1. alarmı sil.")
        print(f"Gemini: {response}")

    except Exception as e:
        print(f"Test skipped or failed: {e}")
