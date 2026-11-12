import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

# --- إعدادات البوت الأساسية ---
API_TOKEN = "YOUR_BOT_TOKEN_HERE"  # ضع توكن بوت الاستضافة هنا
ADMIN_ID = 7753146356  # أيدي المالك الأساسي

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# --- قاعدة بيانات الذاكرة المؤقتة (يمكنك ربطها بـ SQLite أو JSON لاحقاً) ---
# أسعار الاشتراكات الافتراضية
subscription_prices = {
    "7_days": {"days": 7, "stars": 50, "name": "7 أيام"},
    "1_month": {"days": 30, "stars": 100, "name": "شهر"},
    "6_months": {"days": 180, "stars": 300, "name": "6 أشهر"},
    "1_year": {"days": 365, "stars": 1300, "name": "سنة"}
}

# تخزين صلاحيات المستخدمين (عدد البوتات المسموح بها، حالة الـ VIP، الأيام المتبقية)
# format: {user_id: {"bots_limit": 1, "vip": True, "expire_date": "2027-01-01"}}
users_db = {}

# تخزين البوتات المرفوعة للمستخدمين
# format: {user_id: [ {"bot_name": "...", "file_path": "..."}, ... ]}
user_bots = {}


# --- لوحة التحكم والبداية ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        # افتراضياً كل مستخدم جديد لديه صلاحية رفع بوت واحد (إذا كان VIP أو حسب النظام)
        users_db[user_id] = {"bots_limit": 1, "vip": False, "expire_date": "غير مشترك"}

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 إدارة وبوتاتي", callback_data="my_bots")],
        [InlineKeyboardButton(text="💎 اشتراكات VIP والأسعار", callback_data="subscriptions_menu")],
        [InlineKeyboardButton(text="⚙️ لوحة الإدارة", callback_data="admin_panel")] if user_id == ADMIN_ID else []
    ])
    # إزالة الأزرار الفارغة إن وجدت
    keyboard.inline_keyboard = [row for row in keyboard.inline_keyboard if row]

    await message.answer(
        "مرحباً بك في منصة استضافة البوتات المتطورة 🚀
"
        "يمكنك رفع بوتك وتدبير اشتراكاتك بكل سهولة.",
        reply_markup=keyboard
    )


# --- قسم الاشتراكات بالأزرار ---
@router.callback_query(F.data == "subscriptions_menu")
async def subscriptions_menu(callback: CallbackQuery):
    keyboard_buttons = []
    for key, data in subscription_prices.items():
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{data['name']} - {data['stars']} نجمة ⭐",
                callback_data=f"buy_{key}"
            )
        ])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back_home")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(
        "💎 **قسم الاشتراكات والنجوم**

"
        "اختر الباقة المناسبة لك لتفعيل أو تمديد اشتراكك وزيادة عدد بوتاتك:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("buy_"))
async def process_subscription_buy(callback: CallbackQuery):
    sub_key = callback.data.split("_", 1)[1]
    if sub_key not in subscription_prices:
        await callback.answer("الباقة غير موجودة!", show_alert=True)
        return

    plan = subscription_prices[sub_key]
    user = callback.from_user
    
    # إرسال رسالة للمالك
    admin_text = (
        f"🚨 **طلب اشتراك جديد!**

"
        f"👤 الاسم: {user.full_name}
"
        f"🔗 اليوزر: @{user.username or 'لا يوجد'}
"
        f"🆔 الأيدي: `{user.id}`
"
        f"📦 الباقة المطلوبة: {plan['name']}
"
        f"⭐ التكلفة: {plan['stars']} نجمة"
    )
    
    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ قبول وتفعيل", callback_data=f"accept_sub_{user.id}_{sub_key}")],
                [InlineKeyboardButton(text="❌ رفض", callback_data=f"reject_sub_{user.id}")]
            ]),
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Failed to send message to admin: {e}")

    # الرد للمستخدم
    await callback.message.edit_text(
        f"✅ **تم إرسال طلب اشتراكاتك بنجاح!**

"
        f"📦 الباقة: {plan['name']} ({plan['stars']} نجمة)

"
        f"يرجى مراسلة المالك لتسليمه النجوم وتفعيل اشتراكك فوراً:
"
        f"@ASADALY1

"
        f"مرحباً يامبرمجنا، تم طلب اشتراك (مدة: {plan['name']}) والأيدي الخاص بي (`{user.id}`). سوف أرسل النجوم وفعلي اشتراكي.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📨 مراسلة المالك", url="https://t.me/ASADALY1")],
            [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="back_home")]
        ]),
        parse_mode="Markdown"
    )


# --- لوحة التحكم الخاصة بالمالك (الإدارة) ---
@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("هذا القسم خاص بمالك البوت فقط!", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ تعديل أسعار الاشتراكات", callback_data="admin_edit_prices")],
        [InlineKeyboardButton(text="👥 إدارة المستخدمين وصلاحيات الـ VIP", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_home")]
    ])
    await callback.message.edit_text("⚙️ **لوحة تحكم المالك الرئيسية**", reply_markup=keyboard)


@router.callback_query(F.data == "admin_edit_prices")
async def admin_edit_prices(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    text = "✏️ **الأسعار الحالية:**

"
    for key, data in subscription_prices.items():
        text += f"- {data['name']}: {data['stars']} نجمة
"
    
    text += "
لإدارة أو تعديل الأسعار، يمكنك التواصل عبر تطوير الكود أو ربطها بقاعدة بيانات مباشرة."
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع للإدارة", callback_data="admin_panel")]
        ])
    )


# قبول الاشتراك من قبل المالك
@router.callback_query(F.data.startswith("accept_sub_"))
async def accept_subscription(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    _, _, target_user_id, sub_key = callback.data.split("_")
    target_user_id = int(target_user_id)
    
    if target_user_id in users_db:
        users_db[target_user_id]["vip"] = True
        # زيادة صلاحية رفع بوت إضافي أو حسب الحاجة
        users_db[target_user_id]["bots_limit"] += 1

    try:
        await bot.send_message(
            target_user_id,
            "🎉 **مبروك! تم تفعيل اشتراكك بنجاح من قبل المالك.**
يمكنك الآن رفع بوتك واستخدام كافة الميزات المتاحة."
        )
    except Exception:
        pass

    await callback.message.edit_text(callback.message.text + "

✅ **تم قبول وتفعيل الاشتراك بنجاح!**")


@router.callback_query(F.data == "back_home")
async def back_home(callback: CallbackQuery):
    await cmd_start(callback.message)


# --- زر رفع ملفات البوت والمتطلبات requirements.txt ---
@router.callback_query(F.data == "my_bots")
async def my_bots_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = users_db.get(user_id, {"bots_limit": 1, "vip": False})
    current_bots = len(user_bots.get(user_id, []))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 رفع بوت جديد (مع ملف requirements.txt)", callback_data="upload_bot_guide")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_home")]
    ])
    
    await callback.message.edit_text(
        f"🤖 **إدارة بوتاتك والاستضافة**

"
        f"📊 عدد البوتات المرفوعة: {current_bots} / {user_data['bots_limit']}
"
        f"💎 حالة الـ VIP: {'مشترك ✅' if user_data['vip'] else 'عادي ❌'}

"
        f"لرفع بوت جديد، يرجى إرسال ملف البوت (.py) وملف المتطلبات (`requirements.txt`) إن وجد.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def main():
    dp.include_router(router)
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    # asyncio.run(main())
    pass