import os
import logging
import asyncio
from datetime import time as dt_time
import pytz
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from ai_agent import MarketAIAgent
from notification_service import (
    check_alerts, add_alert, save_snapshot, generate_newsletter, 
    subscribe_newsletter, unsubscribe_newsletter, get_newsletter_subscribers
)

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize AI Agent
# We initialize it globally for simplicity, though per-user session is better for context.
# For now, a shared agent or re-instantiated agent is fine.
# Re-instantiating per chat is safer for context isolation if 'history' is used.
# But MarketAIAgent keeps state in self.chat. Let's make a helper to get/create agent per user_id if we want history.
# For simplicity in this v1, we will re-create agent or use a global one without history persistence across restarts.
# Let's use a simple global cache for agents.
agents = {}

def get_agent(user_id):
    if user_id not in agents:
        try:
            agents[user_id] = MarketAIAgent(user_id=user_id)
        except ValueError as e:
            logging.error(f"Failed to create agent: {e}")
            return None
    return agents[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subscribe_newsletter(user_id) # Auto subscribe
    
    await update.message.reply_text(
        "Merhaba! Ben Gemini destekli Piyasa Takip Botuyum. 🤖\n\n"
        "Şunları yapabilirim:\n"
        "✅ **Fiyat Alarmı:** 'THYAO 300 olunca haber ver'\n"
        "✅ **Zamanlayıcı:** '10 dakika sonra fırını kapat'\n"
        "✅ **Bakiye Takibi:** '500 gram altınım var', 'Durumum ne?'\n"
        "✅ **Haber Bülteni:** Her gün 08:00 ve 18:00'de rapor (Otomatik aktif)\n\n"
        "Konuşmaya başlayabiliriz! (İptal için: /iptal_bulten)"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Komutlar:\n"
        "/start - Botu başlat\n"
        "/help - Yardımı göster\n"
        "/alert <symbol> <price> <above|below> - Alarm kur (Örn: /alert THYAO 300 above)\n"
        "Veya doğrudan doğal dille sorular sorabilirsiniz."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    agent = get_agent(user_id)
    if not agent:
        await update.message.reply_text("AI servisi şu anda kullanılamıyor (API Key hatası olabilir).")
        return

    # Indicate typing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # Run AI blocking call in executor to avoid blocking asyncio loop
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, agent.send_message, user_message)
    
    await update.message.reply_text(response)

async def set_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Format: /alert <symbol> <target> <condition>
    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text("Hatalı format. Kullanım: /alert <symbol> <price> <above|below>\nÖrn: /alert THYAO 300 above")
            return
            
        symbol = args[0]
        target = args[1]
        condition = args[2] # above or below
        
        if condition not in ['above', 'below']:
            await update.message.reply_text("Koşul 'above' (yukarı) veya 'below' (aşağı) olmalıdır.")
            return
            
        result = add_alert(symbol, target, condition, update.effective_user.id)
        await update.message.reply_text(f"{result} ({symbol} {condition} {target})")
        
    except Exception as e:
        await update.message.reply_text(f"Hata oluştu: {e}")

async def check_alerts_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Periodic job to check alerts.
    """
    triggered = check_alerts()
    for item in triggered:
        user_id = item['user_id']
        message = item['message']
        repeat_count = item.get('repeat_count', 1)
        
        try:
            for i in range(repeat_count):
                if i > 0:
                    # Delay calculation as requested: 0.75 * (i+1)
                    # wait time increases? Or wait between?
                    # "3. bildirim 750ms * 3 = 2.25 sn sonra gönderilsin"
                    # User request: "birinci bildirim 750ms sonra" (implies intial wait too, or wait between?)
                    # Let's interpret: wait BEFORE sending specific repetition.
                    # Actually for 1st notif usually immediate. User said "ilk bildirim 750ms * 1 = 750ms sonra".
                    delay = 0.75 * (i + 1)
                    await asyncio.sleep(delay)
                    
                await context.bot.send_message(chat_id=user_id, text=message)
                
                # Small buffer if logic implies cumulative wait, but prompt implies individual sleep.
                # If "3rd notification sent 2.25s after", it means relative to START or relative to Previous?
                # "ilk bildirim ... 750ms sonra" -> Wait 0.75, send.
                # "2. bildirim (i=1) ... 750 * 2 = 1.5s sonra" -> Wait 1.5s, send?
                # If we await sleep inside loop, it is sequential. 
                # i=0: sleep(0.75), send.
                # i=1: sleep(1.5), send. (Total time from start = 0.75 + 1.5 = 2.25).
                # User's example: "3. bildirim 2.25sn sonra".
                # If i=0 takes 0.75, i=1 takes 1.5. i=2 (3rd msg) takes 2.25.
                # Wait, 0.75 + 1.5 + 2.25 = 4.5s total.
                # Or meant: 3rd notification is sent at T+2.25s?
                # "Mesela 3. bildirim 750ms * 3 = 2.25 sn sonra gönderilsin." -> This likely means absolute time from trigger?
                # But since we can't go back in time or parallel easily in simple loop without spawning tasks:
                # If we want 3 messages at T+0.75, T+1.5, T+2.25:
                # Sleep(0.75) -> Send 1.
                # Sleep(0.75) -> Send 2 (total 1.5).
                # Sleep(0.75) -> Send 3 (total 2.25).
                # YES. Consistent interval of 750ms satisfies the math 0.75*N.
                # 0.75 * 1 = 0.75
                # 0.75 * 2 = 1.5 (0.75 + 0.75)
                # 0.75 * 3 = 2.25 (0.75 + 0.75 + 0.75)
                # So we just sleep 0.75 each time!
                if i == 0:
                     # Since user said "ilk bildirim 750ms * 1 = 750ms sonra", we wait 0.75 even for first.
                     await asyncio.sleep(0.75)
                await context.bot.send_message(chat_id=user_id, text=message)
        
        except Exception as e:
            logging.error(f"Failed to send alert to {user_id}: {e}")

async def iptal_bulten_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = unsubscribe_newsletter(user_id)
    await update.message.reply_text(msg)

async def newsletter_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Runs daily to send newsletters.
    """
    # Context data should carry the label ('morning' or 'evening')
    label = context.job.data
    
    # 1. Save global snapshot first
    save_snapshot(label)
    
    # 2. Send to subscribers
    subs = get_newsletter_subscribers()
    for user_id in subs:
        try:
            report = generate_newsletter(user_id, label)
            if report:
                await context.bot.send_message(chat_id=user_id, text=report)
        except Exception as e:
            logging.error(f"Newsletter failed for {user_id}: {e}")

async def run_bot():
    """
    Starts the bot.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found.")
        return

    application = ApplicationBuilder().token(token).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("alert", set_alert_command))
    application.add_handler(CommandHandler("iptal_bulten", iptal_bulten_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Jobs
    if application.job_queue:
        # Start startup check
        application.job_queue.run_repeating(check_alerts_job, interval=5, first=1)
        
        # Newsletter Jobs (Timezone: Europe/Istanbul)
        tz = pytz.timezone("Europe/Istanbul")
        
        # Morning 08:00
        application.job_queue.run_daily(
            newsletter_job, 
            time=dt_time(hour=8, minute=0, tzinfo=tz),
            data='morning',
            name='newsletter_morning'
        )
        
        # Evening 18:00
        application.job_queue.run_daily(
            newsletter_job, 
            time=dt_time(hour=18, minute=0, tzinfo=tz),
            data='evening',
            name='newsletter_evening'
        )
        
        # For TESTING: Run once immediately (remove in prod or comment out)
        # application.job_queue.run_once(newsletter_job, when=5, data='evening')

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    asyncio.run(run_bot())
