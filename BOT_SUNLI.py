import os
import re
import json
import random
import uuid
import asyncio
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CẤU HÌNH HỆ THỐNG CỦA BẠN =================
TOKEN = "8983558939:AAGM2jgz6PagWJaPwcOsTzUzeH7mir1baBM"
ADMIN_ID = 7048433382
ADMIN_GROUP_ID = 7048433382

# CẤU HÌNH KÊNH & LIÊN HỆ
USER_CHANNEL_LINK = "https://t.me/vanminhpre"
ADMIN_CONTACT_LINK = "https://t.me/orion011"
USER_CHANNEL_ID = "@vanminhpre"

# CẤU HÌNH ĐẤU NỐI ĐA NGUỒN API (CANBOSO.COM + BOTDAVID.IO.VN)
SUPPLIERS = {
    "canboso": {
        "name": "canboso.com",
        "base_url": "https://canboso.com",
        "api_key": "tgb_c4df682ad0774092b11d6e6507af47d9bc7b240233c5bb97",
        "prefix": "api"
    },
    "botdavid": {
        "name": "botdavid.io.vn",
        "base_url": "https://botdavid.io.vn",
        "api_key": "c2e55776e0cdcc0c2006b93053aa14b66167c0febd2ddcac",
        "prefix": "david"
    }
}

# FILE LƯU TRỮ DỮ LIỆU VĨNH VIỄN
BLOCKED_FILE = "sanpham_da_xoa.json"
CUSTOM_PRICES_FILE = "gia_tuy_chinh.json"
CUSTOM_LOGOS_FILE = "logo_san_pham.json"
USERS_FILE = "users_database.json"

DEFAULT_BLOCKED = {
    "api_6a9e637c4f6e4dbc77f68033",
    "api_6add9d0cbe0925eeb509e9c7"
}

# BỘ LOGO CUSTOM EMOJI MẶC ĐỊNH (BẠN CÓ THỂ CẬP NHẬT THÊM BẰNG LỆNH /setlogo)
DEFAULT_CUSTOM_LOGOS = {}

# THÔNG TIN NGÂN HÀNG NHẬN TIỀN VIETQR
BANK_ID = "MB"
ACCOUNT_NO = "0979770049"
ACCOUNT_NAME = "BUI VAN MINH"

PRODUCTS = {
    "canva": {
        "name": "Canva Pro 1 Năm",
        "price": 39000,
        "desc": "Nâng cấp chính chủ, bảo hành full thời gian sử dụng.",
        "file": "kho_canva.txt",
        "source": "local"
    }
}

PENDING_ORDERS = {}
# =============================================================

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    users = load_users()
    str_id = str(user_id)
    if str_id not in users:
        users[str_id] = {"balance": 0, "history": []}
        save_users(users)
    return users[str_id]

def add_user_history(user_id, order_code, product_name, amount):
    users = load_users()
    str_id = str(user_id)
    if str_id not in users:
        users[str_id] = {"balance": 0, "history": []}
    users[str_id]["history"].append({
        "order_code": order_code,
        "product": product_name,
        "amount": amount
    })
    save_users(users)

def format_account_delivery(raw_data):
    try:
        if isinstance(raw_data, str):
            raw_str = raw_data.strip()
            if raw_str.startswith("{") and raw_str.endswith("}"):
                data = json.loads(raw_str)
            else:
                if "|" in raw_str:
                    parts = raw_str.split("|", 1)
                    return (
                        f"👤 **Tài khoản:** `{parts[0].strip()}`\n"
                        f"🔐 **Mật khẩu:** `{parts[1].strip()}`\n"
                        f"📋 **Copy nhanh:** `{raw_str}`"
                    )
                return f"`{raw_str}`"
        elif isinstance(raw_data, dict):
            data = raw_data
        else:
            return f"`{str(raw_data)}`"

        accounts = (
            data.get("delivery", {}).get("accounts")
            or data.get("data", {}).get("accounts")
            or data.get("order", {}).get("accounts")
            or data.get("accounts")
            or []
        )
        if not accounts and isinstance(data.get("data"), list):
            accounts = data.get("data")

        if accounts and isinstance(accounts, list):
            formatted_list = []
            for idx, acc in enumerate(accounts, 1):
                if isinstance(acc, dict):
                    u = str(acc.get("user") or acc.get("username") or acc.get("email") or acc.get("account") or "").strip()
                    p = str(acc.get("password") or acc.get("pass") or acc.get("mk") or "").strip()
                    exp = acc.get("expiryText") or acc.get("expiry")
                    other = acc.get("otherInfo") or acc.get("note")

                    if "|" in u and not p:
                        u_parts = u.split("|", 1)
                        u_clean = u_parts[0].strip()
                        p_clean = u_parts[1].strip()
                        full_line = u
                    else:
                        u_clean = u
                        p_clean = p
                        full_line = f"{u_clean}|{p_clean}" if p_clean else u_clean

                    prefix = f"🔹 **Acc #{idx}:**\n" if len(accounts) > 1 else ""
                    if p_clean:
                        item_text = (
                            f"{prefix}"
                            f"👤 **Tài khoản:** `{u_clean}`\n"
                            f"🔐 **Mật khẩu:** `{p_clean}`\n"
                            f"📋 **Copy nhanh:** `{full_line}`"
                        )
                    else:
                        item_text = f"{prefix}🔑 **Tài khoản:** `{full_line}`"

                    if exp:
                        item_text += f"\n⏳ **Hạn dùng:** `{exp}`"
                    if other:
                        item_text += f"\n📝 **Ghi chú:** `{other}`"
                    formatted_list.append(item_text)
                elif isinstance(acc, str):
                    if "|" in acc:
                        parts = acc.split("|", 1)
                        formatted_list.append(
                            f"👤 **Tài khoản:** `{parts[0].strip()}`\n"
                            f"🔐 **Mật khẩu:** `{parts[1].strip()}`\n"
                            f"📋 **Copy nhanh:** `{acc.strip()}`"
                        )
                    else:
                        formatted_list.append(f"🔑 **Tài khoản:** `{acc.strip()}`")
                else:
                    formatted_list.append(f"`{str(acc)}`")

            if formatted_list:
                return "\n\n".join(formatted_list)

        for key_fb in ["account", "data", "item", "result", "key", "code"]:
            fallback = data.get(key_fb)
            if isinstance(fallback, str) and fallback.strip():
                if "|" in fallback:
                    parts = fallback.split("|", 1)
                    return (
                        f"👤 **Tài khoản:** `{parts[0].strip()}`\n"
                        f"🔐 **Mật khẩu:** `{parts[1].strip()}`\n"
                        f"📋 **Copy nhanh:** `{fallback.strip()}`"
                    )
                return f"`{fallback.strip()}`"

        return f"`{json.dumps(data, ensure_ascii=False)}`"
    except Exception:
        return f"`{str(raw_data)}`"

def load_blocked_keys():
    blocked = set(DEFAULT_BLOCKED)
    if os.path.exists(BLOCKED_FILE):
        try:
            with open(BLOCKED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        blocked.add(str(item).strip().lower())
        except Exception:
            pass
    return blocked

def save_blocked_keys(keys_list):
    blocked = load_blocked_keys()
    for k in keys_list:
        clean_k = str(k).strip().lower()
        if clean_k:
            blocked.add(clean_k)
    with open(BLOCKED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(blocked), f, ensure_ascii=False, indent=2)

def load_custom_prices():
    if not os.path.exists(CUSTOM_PRICES_FILE):
        return {}
    try:
        with open(CUSTOM_PRICES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_custom_price(code, new_price):
    prices = load_custom_prices()
    prices[code.lower()] = int(new_price)
    with open(CUSTOM_PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)

def load_custom_logos():
    logos = dict(DEFAULT_CUSTOM_LOGOS)
    if os.path.exists(CUSTOM_LOGOS_FILE):
        try:
            with open(CUSTOM_LOGOS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    logos.update(saved)
        except Exception:
            pass
    return logos

def save_custom_logo(keyword, emoji_id):
    logos = load_custom_logos()
    logos[keyword.lower()] = str(emoji_id).strip()
    with open(CUSTOM_LOGOS_FILE, "w", encoding="utf-8") as f:
        json.dump(logos, f, ensure_ascii=False, indent=2)

def clean_product_title(name):
    """Làm sạch các emoji rác ở đầu tên sản phẩm để hiển thị Logo Premium thẳng hàng"""
    cleaned = re.sub(r'^[\s✨🔥💎⚡🎬🎨▶️🤖🧠🐳🌌🍿🎵🎼🅰️📐🛡️🟢🏔️🦈🔑🪟📊✈️💬🎮💻🌸📧🔵💫📓]+', '', str(name))
    return cleaned.strip() or str(name)

def get_product_icon_and_logo(prod_key, prod_name):
    name_lower = prod_name.lower()
    key_lower = prod_key.lower()
    custom_logos = load_custom_logos()
    
    # Ưu tiên khớp chính xác mã sản phẩm trước, sau đó khớp theo từ khóa trong tên
    custom_emoji_id = custom_logos.get(key_lower)
    if not custom_emoji_id:
        for kw, eid in custom_logos.items():
            if kw in name_lower or kw in key_lower:
                custom_emoji_id = eid
                break
    
    std_icon = "💎"
    brand_icons = {
        "canva": "🎨", "capcut": "🎬", "gemini": "✨", "veo": "✨", "google": "✨",
        "gpt": "🤖", "chatgpt": "🤖", "openai": "🤖", "copilot": "🤖",
        "claude": "🧠", "deepseek": "🐳", "grok": "🌌", "netflix": "🍿",
        "youtube": "▶️", "ytb": "▶️", "spotify": "🎵", "suno": "🎼",
        "adobe": "🅰️", "photoshop": "🅰️", "premiere": "🎬", "illustrator": "🎨",
        "figma": "📐", "vpn": "🛡️", "proton": "🛡️", "hma": "🛡️",
        "duolingo": "🟢", "nord": "🏔️", "surfshark": "🦈", "key": "🔑",
        "window": "🪟", "office": "📊", "telegram": "✈️", "zalo": "💬",
        "discord": "🎮", "vps": "💻", "meitu": "🌸", "gmail": "📧",
        "zoom": "🔵", "higg": "⚡", "wink": "💫", "notion": "📓", "tiktok": "🎵",
        "facebook": "📘", "instagram": "📸", "github": "🐙", "tinder": "🔥"
    }
    for brand_kw, icon in brand_icons.items():
        if brand_kw in name_lower or brand_kw in key_lower:
            std_icon = icon
            break
    return std_icon, custom_emoji_id

def create_styled_button(text, callback_data=None, url=None, custom_emoji_id=None, fallback_icon=""):
    """Hàm tạo nút bấm hỗ trợ gắn trực tiếp Custom Emoji ID của Telegram Premium"""
    if custom_emoji_id:
        try:
            if url:
                return InlineKeyboardButton(text, url=url, api_kwargs={"icon_custom_emoji_id": str(custom_emoji_id)})
            return InlineKeyboardButton(text, callback_data=callback_data, api_kwargs={"icon_custom_emoji_id": str(custom_emoji_id)})
        except Exception:
            pass
    display_text = f"{fallback_icon} {text}".strip() if fallback_icon else text
    if url:
        return InlineKeyboardButton(display_text, url=url)
    return InlineKeyboardButton(display_text, callback_data=callback_data)

def apply_saved_prices():
    custom_prices = load_custom_prices()
    for k, val in custom_prices.items():
        if k in PRODUCTS:
            PRODUCTS[k]["price"] = int(val)

def extract_number(val, default=0):
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        digits = "".join(ch for ch in val if ch.isdigit())
        return int(digits) if digits else default
    if isinstance(val, dict):
        for k in ["amount", "value", "price", "vnd", "retail", "cost"]:
            if k in val and isinstance(val[k], (int, float, str)):
                res = extract_number(val[k], -1)
                if res != -1:
                    return res
        for v in val.values():
            if isinstance(v, (int, float)):
                return int(v)
    return default

def extract_text(val, default=""):
    if val is None:
        return default
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        for k in ["vi", "vn", "name", "title", "text"]:
            if k in val and isinstance(val[k], str):
                return val[k]
        for v in val.values():
            if isinstance(v, str):
                return v
    return str(val)

def call_supplier_api(supplier_key, endpoint, method="GET", payload=None, extra_headers=None):
    sup = SUPPLIERS.get(supplier_key)
    if not sup:
        return None, f"Không tìm thấy nguồn: {supplier_key}"
    base_url = sup["base_url"].rstrip("/")
    api_key = sup["api_key"]
    url = f"{base_url}{endpoint}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "x-api-key": api_key,
        "Authorization": f"Bearer {api_key}"
    }
    if extra_headers:
        headers.update(extra_headers)
    data_bytes = json.dumps(payload).encode("utf-8") if payload else None
    req = Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"
    except Exception as e:
        return None, str(e)

def fetch_supplier_products(supplier_key):
    endpoints = [
        "/api/v2/telegram-buyer/products",
        "/api/v1/telegram-buyer/products",
        "/api/telegram-buyer/products",
        "/api/v1/products",
        "/api/products"
    ]
    last_err = ""
    for ep in endpoints:
        data, err = call_supplier_api(supplier_key, ep, method="GET")
        if not err and data:
            return data, None
        if err:
            last_err = err
            if "HTTP 401" in err or "HTTP 403" in err:
                break
    return None, last_err

def sync_api_products():
    blocked_keys = load_blocked_keys()
    custom_prices = load_custom_prices()
    for b_key in list(PRODUCTS.keys()):
        if b_key.lower() in blocked_keys:
            del PRODUCTS[b_key]

    summary_msgs = []
    any_success = False

    for sup_key, sup_cfg in SUPPLIERS.items():
        data, err = fetch_supplier_products(sup_key)
        if err or not data:
            summary_msgs.append(f"❌ {sup_cfg['name']}: Lỗi")
            continue

        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for k in ["data", "products", "items", "result", "categories"]:
                if k in data and isinstance(data[k], list):
                    if k == "categories" and data[k] and isinstance(data[k][0], dict) and "products" in data[k][0]:
                        for cat in data[k]:
                            if isinstance(cat.get("products"), list):
                                items.extend(cat["products"])
                    else:
                        items = data[k]
                    break

        count = 0
        prefix = sup_cfg.get("prefix", sup_key)
        for item in items:
            if not isinstance(item, dict):
                continue
            prod_id = item.get("id") or item.get("productId") or item.get("code")
            name = extract_text(item.get("name") or item.get("title"), f"Sản phẩm #{prod_id}")
            base_price = extract_number(item.get("price") or item.get("amount"), 0)
            stock = extract_number(item.get("stock") or item.get("quantity"), 1)
            raw_desc = item.get("description") or item.get("desc") or "Giao tài khoản tự động 24/7."
            desc_text = extract_text(raw_desc, "Giao tài khoản tự động")
            if len(desc_text) > 80:
                desc_text = desc_text[:77] + "..."

            if prod_id is not None:
                key = f"{prefix}_{str(prod_id)[:40]}".lower()
                if key in blocked_keys or str(prod_id).lower() in blocked_keys:
                    continue
                
                calculated_price = int(base_price * 1.3)
                final_price = custom_prices.get(key, calculated_price)

                PRODUCTS[key] = {
                    "name": name,
                    "base_price": base_price,
                    "price": final_price,
                    "desc": desc_text,
                    "stock": stock,
                    "api_id": prod_id,
                    "source": "api",
                    "supplier": sup_key
                }
                count += 1
        any_success = True
        summary_msgs.append(f"✅ {sup_cfg['name']}: {count} SP")

    apply_saved_prices()
    return any_success, " | ".join(summary_msgs), None

def purchase_from_api(supplier_key, api_prod_id, quantity=1):
    payload = {"productId": api_prod_id, "product_id": api_prod_id, "quantity": quantity, "amount": quantity}
    idempotency_key = str(uuid.uuid4())
    headers = {"Idempotency-Key": idempotency_key}
    endpoints = [
        "/api/v2/telegram-buyer/purchase",
        "/api/v1/telegram-buyer/purchase",
        "/api/telegram-buyer/purchase",
        "/api/purchase"
    ]
    last_err = ""
    for ep in endpoints:
        data, err = call_supplier_api(supplier_key, ep, method="POST", payload=payload, extra_headers=headers)
        if not err and data:
            return True, data
        if err:
            last_err = err
            if "HTTP 404" not in err:
                break
    return False, f"Lỗi gọi API ({supplier_key}): {last_err}"

def init_stock_files():
    for key, item in PRODUCTS.items():
        if item.get("source") == "local" and not os.path.exists(item["file"]):
            with open(item["file"], "w", encoding="utf-8") as f:
                pass

def get_item_stock(item):
    if item.get("source") == "api":
        return item.get("stock", 0)
    filename = item.get("file", "")
    if not os.path.exists(filename):
        return 0
    with open(filename, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    return len(lines)

def pop_stock_item(filename):
    if not os.path.exists(filename):
        return None
    with open(filename, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    if not lines:
        return None
    item = lines[0]
    with open(filename, "w", encoding="utf-8") as f:
        for line in lines[1:]:
            f.write(line + "\n")
    return item

def download_qr_image(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=12) as response:
        return response.read()

def is_admin(update: Update):
    user_id = update.effective_user.id if update.effective_user else 0
    chat_id = update.effective_chat.id if update.effective_chat else 0
    return user_id == ADMIN_ID or chat_id == ADMIN_GROUP_ID

def get_main_menu_keyboard():
    """Tạo Menu chính hỗ trợ gắn cả Custom Emoji Premium lên từng nút"""
    logos = load_custom_logos()
    keyboard = [
        [create_styled_button("Mua hàng", callback_data="back_to_menu", custom_emoji_id=logos.get("menu_muahang"), fallback_icon="🛒")],
        [
            create_styled_button("Hồ sơ", callback_data="menu_profile", custom_emoji_id=logos.get("menu_hoso"), fallback_icon="👤"),
            create_styled_button("Lịch sử mua", callback_data="menu_history", custom_emoji_id=logos.get("menu_lichsu"), fallback_icon="🧿")
        ],
        [create_styled_button("Ví", callback_data="menu_wallet", custom_emoji_id=logos.get("menu_vi"), fallback_icon="👛")],
        [create_styled_button("Hỗ trợ", url=ADMIN_CONTACT_LINK, custom_emoji_id=logos.get("menu_hotro"), fallback_icon="💬")],
        [create_styled_button("API", callback_data="menu_api", custom_emoji_id=logos.get("menu_api"), fallback_icon="🔗")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def post_init(application):
    init_stock_files()
    sync_api_products()
    commands = [
        BotCommand("start", "Bắt đầu sử dụng bot"),
        BotCommand("menu", "Xem danh sách sản phẩm"),
        BotCommand("qtv", "Bảng điều khiển quản trị"),
    ]
    await application.bot.set_my_commands(commands)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "bạn"
    text = (
        f"📌 **Vui lòng chọn menu:**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👋 Chào mừng **{user_name}** đến với **SHOPTAIKHOAN SUNLI**!\n"
        f"⚡ Hệ thống cung cấp tài khoản Premium tự động 24/7."
    )
    if is_admin(update):
        text += "\n\n👑 *[QTV] Dùng lệnh `/qtv` để quản lý shop & gắn Emoji Premium.*"

    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())
    elif update.callback_query:
        try:
            await update.callback_query.message.delete()
        except Exception:
            pass
        await update.callback_query.message.chat.send_message(text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())

async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    help_text = (
        "👑 **BẢNG ĐIỀU KHIỂN - SHOPTAIKHOAN SUNLI:**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎨 **QUẢN LÝ LOGO EMOJI PREMIUM:**\n"
        "• `/setlogo <từ_khóa> <thả_Emoji_Premium>` : Gắn Logo cho sản phẩm (Hỗ trợ gắn nhiều từ khóa cùng lúc!)\n"
        "  *VD:* `/setlogo capcut 🎬 gpt 🤖 youtube ▶️`\n"
        "• **Đổi icon cho nút Menu Chính:** Dùng từ khóa `menu_muahang`, `menu_hoso`, `menu_lichsu`, `menu_vi`, `menu_hotro`, `menu_api` kèm Emoji.\n"
        "• `/dslogo` : Xem các Logo Emoji Premium đang gắn\n"
        "• `/xoalogo <từ_khóa>` : Xóa Logo của từ khóa\n"
        "• `/layid <thả_Emoji_Premium>` : Lấy mã ID của Emoji bất kỳ\n\n"
        "📦 **QUẢN LÝ KHO & SẢN PHẨM:**\n"
        "• `/kho` : Xem sản phẩm & tồn kho\n"
        "• `/doigia <mã> <giá>` : Đổi giá sản phẩm\n"
        "• `/themkho <mã> <acc>` : Nạp kho .txt\n"
        "• `/themsanpham <mã> | <tên> | <giá> | <mô_tả>`\n"
        "• `/xoasanpham <mã>` : Xóa sản phẩm\n"
        "• `/api` : Đồng bộ API"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def get_emoji_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh giúp QTV thả các icon từ bộ Application Emoji vào để lấy mã ID nhanh"""
    if not is_admin(update):
        return
    if not update.message.entities:
        await update.message.reply_text(
            "💡 **CÁCH LẤY MÃ EMOJI PREMIUM:**\n"
            "Hãy gõ `/layid ` sau đó bấm chọn các icon từ bảng **Application Emoji** của bạn rồi gửi tin nhắn!",
            parse_mode="Markdown"
        )
        return
        
    found = []
    text = update.message.text
    for ent in update.message.entities:
        if ent.type == "custom_emoji" and ent.custom_emoji_id:
            char = text[ent.offset : ent.offset + ent.length]
            found.append(f"• Icon {char} ➡️ ID: `{ent.custom_emoji_id}`")
            
    if not found:
        await update.message.reply_text("⚠️ Đó là emoji thường, không phải Emoji Premium (Custom Emoji)!", parse_mode="Markdown")
        return
        
    await update.message.reply_text("🎉 **DANH SÁCH MÃ CUSTOM EMOJI:**\n\n" + "\n".join(found), parse_mode="Markdown")

async def set_logo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hỗ trợ gắn 1 hoặc NHIỀU Logo Emoji Premium cùng lúc chỉ bằng 1 tin nhắn"""
    if not is_admin(update):
        return
    text = update.message.text or ""
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text(
            "🎨 **CÁCH GẮN LOGO THƯƠNG HIỆU LÊN NÚT BẤM:**\n\n"
            "1️⃣ **Gắn 1 sản phẩm:**\n"
            "`/setlogo capcut <chọn_Emoji_CapCut>`\n\n"
            "2️⃣ **Gắn hàng loạt sản phẩm cùng lúc:**\n"
            "`/setlogo capcut <Emoji> youtube <Emoji> gpt <Emoji> netflix <Emoji>`\n\n"
            "3️⃣ **Gắn cho Menu chính:**\n"
            "`/setlogo menu_muahang <Emoji> menu_vi <Emoji>`",
            parse_mode="Markdown"
        )
        return

    # Thu thập toàn bộ custom_emoji trong tin nhắn theo thứ tự xuất hiện
    custom_emojis = []
    if update.message.entities:
        for ent in update.message.entities:
            if ent.type == "custom_emoji" and ent.custom_emoji_id:
                custom_emojis.append((ent.offset, ent.length, ent.custom_emoji_id))

    saved_pairs = []

    # Nếu người dùng thả trực tiếp Emoji Premium từ bảng Application Emoji
    if custom_emojis:
        # Tách các từ khóa nằm trước mỗi custom emoji
        last_pos = len(parts[0])  # Bỏ qua chữ '/setlogo'
        for offset, length, eid in custom_emojis:
            segment = text[last_pos:offset].strip()
            words = [w.strip().lower() for w in segment.split() if w.strip()]
            if words:
                kw = words[-1]
                save_custom_logo(kw, eid)
                saved_pairs.append(f"• `{kw}` ➡️ ID `{eid}`")
            last_pos = offset + length

    # Nếu người dùng nhập bằng mã số ID: /setlogo capcut 5368324170671202286
    if not saved_pairs and len(parts) >= 3 and parts[2].isdigit():
        kw = parts[1].strip().lower()
        eid = parts[2].strip()
        save_custom_logo(kw, eid)
        saved_pairs.append(f"• `{kw}` ➡️ ID `{eid}`")

    if not saved_pairs:
        await update.message.reply_text(
            "⚠️ Không tìm thấy **Emoji Premium** trong tin nhắn!\n"
            "👉 Bạn hãy gõ `/setlogo <từ_khóa> <bấm_chọn_icon_từ_bộ_Application_Emoji>` nhé!",
            parse_mode="Markdown"
        )
        return

    msg = "✅ **ĐÃ GẮN LOGO PREMIUM THÀNH CÔNG:**\n" + "\n".join(saved_pairs) + "\n\n👉 Gõ `/menu` hoặc `/start` để xem giao diện mới!"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def list_logos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    logos = load_custom_logos()
    if not logos:
        await update.message.reply_text("📭 Hiện chưa có từ khóa nào được gắn Custom Emoji.", parse_mode="Markdown")
        return
    lines = [f"• `{k}` : `{v}`" for k, v in logos.items()]
    await update.message.reply_text("🎨 **DANH SÁCH LOGO ĐANG GẮN:**\n\n" + "\n".join(lines), parse_mode="Markdown")

async def delete_logo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    parts = update.message.text.split()
    if len(parts) < 2:
        await update.message.reply_text("⚠️ Cách dùng: `/xoalogo <từ_khóa>`", parse_mode="Markdown")
        return
    kw = parts[1].strip().lower()
    logos = load_custom_logos()
    if kw in logos:
        del logos[kw]
        with open(CUSTOM_LOGOS_FILE, "w", encoding="utf-8") as f:
            json.dump(logos, f, ensure_ascii=False, indent=2)
        await update.message.reply_text(f"✅ Đã xóa logo của từ khóa `{kw}`!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Không tìm thấy từ khóa `{kw}`!", parse_mode="Markdown")

async def check_stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    sync_api_products()
    msg = "📦 **DANH SÁCH SẢN PHẨM & TỒN KHO (+30% LỢI NHUẬN):**\n━━━━━━━━━━━━━━━━━━\n"
    for key, item in PRODUCTS.items():
        count = get_item_stock(item)
        std_icon, eid = get_product_icon_and_logo(key, item['name'])
        logo_status = f"✨ Logo Pre (`{eid}`)" if eid else f"Icon thường ({std_icon})"
        msg += f"{std_icon} **{item['name']}**\n  Mã: `{key}` | Giá: **{item['price']:,}đ** | Kho: **{count}** | {logo_status}\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def change_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    parts = update.message.text.split()
    if len(parts) < 3:
        await update.message.reply_text("⚠️ `/doigia <mã> <giá_mới>`", parse_mode="Markdown")
        return
    code, price_str = parts[1].strip().lower(), parts[2].strip()
    if code not in PRODUCTS:
        await update.message.reply_text(f"❌ Không tìm thấy mã `{code}`!", parse_mode="Markdown")
        return
    try:
        new_price = int(''.join(filter(str.isdigit, price_str)))
    except ValueError:
        await update.message.reply_text("❌ Giá phải là số!", parse_mode="Markdown")
        return
    PRODUCTS[code]["price"] = new_price
    save_custom_price(code, new_price)
    await update.message.reply_text(f"✅ Đã đổi giá `{code}` thành **{new_price:,}đ**", parse_mode="Markdown")

async def add_product_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    text = update.message.text.replace("/themsanpham", "").strip()
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 4:
        await update.message.reply_text("⚠️ `/themsanpham <mã> | <tên> | <giá> | <mô_tả>`", parse_mode="Markdown")
        return
    code, name, price_str, desc = parts[0].lower(), parts[1], parts[2], parts[3]
    try:
        price = int(''.join(filter(str.isdigit, price_str)))
    except ValueError:
        await update.message.reply_text("❌ Giá tiền không hợp lệ!", parse_mode="Markdown")
        return
    PRODUCTS[code] = {"name": name, "price": price, "desc": desc, "file": f"kho_{code}.txt", "source": "local"}
    save_custom_price(code, price)
    init_stock_files()
    await update.message.reply_text(f"✅ Thêm sản phẩm `{code}` thành công!", parse_mode="Markdown")

async def delete_product_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    raw_tokens = update.message.text.replace("/xoasanpham", " ").split()
    codes = [t.strip().lower() for t in raw_tokens if t.strip()]
    if not codes:
        await update.message.reply_text("⚠️ `/xoasanpham <mã>`", parse_mode="Markdown")
        return
    save_blocked_keys(codes)
    for code in codes:
        if code in PRODUCTS:
            del PRODUCTS[code]
    await update.message.reply_text("✅ Đã xóa & chặn vĩnh viễn!", parse_mode="Markdown")

async def add_stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    parts = update.message.text.split(maxsplit=2)
    if len(parts) < 3:
        await update.message.reply_text("⚠️ `/themkho <mã> <tài_khoản>`", parse_mode="Markdown")
        return
    prod_key, raw_accounts = parts[1].lower(), parts[2].strip().split("\n")
    if prod_key not in PRODUCTS:
        await update.message.reply_text("❌ Mã sản phẩm không tồn tại!", parse_mode="Markdown")
        return
    product = PRODUCTS[prod_key]
    if product.get("source") == "api":
        await update.message.reply_text("⚠️ Sản phẩm API không dùng kho .txt!", parse_mode="Markdown")
        return
    with open(product["file"], "a", encoding="utf-8") as f:
        for acc in raw_accounts:
            if acc.strip():
                f.write(acc.strip() + "\n")
    await update.message.reply_text(f"✅ Đã nạp thêm vào **{product['name']}**! Tổng: **{get_item_stock(product)}**", parse_mode="Markdown")

async def test_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    ok, msg, _ = sync_api_products()
    await update.message.reply_text(f"🔄 **KẾT QUẢ ĐỒNG BỘ API (+30% GIÁ):**\n{msg}", parse_mode="Markdown")

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_api_products()
    blocked_keys = load_blocked_keys()
    keyboard = []
    for key, item in list(PRODUCTS.items()):
        if key.lower() in blocked_keys:
            continue
        stock = get_item_stock(item)
        price_str = f"{item['price']:,}đ"
        std_icon, custom_emoji_id = get_product_icon_and_logo(key, item["name"])
        clean_name = clean_product_title(item["name"])
        
        if stock > 0:
            label = f"{clean_name} ({price_str}) | Còn: {stock}"
            btn = create_styled_button(
                label,
                callback_data=f"buy|{key}",
                custom_emoji_id=custom_emoji_id,
                fallback_icon=std_icon
            )
        else:
            btn = InlineKeyboardButton(f"❌ {clean_name} ({price_str}) | HẾT HÀNG", callback_data=f"buy|{key}")
            
        keyboard.append([btn])
    
    keyboard.append([InlineKeyboardButton("🔙 Quay lại Menu Chính", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "📋 **MENU SẢN PHẨM - SHOPTAIKHOAN SUNLI**\n━━━━━━━━━━━━━━━━━━\n*(Chạm vào sản phẩm để mua tự động)*"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        try:
            await update.callback_query.message.delete()
        except Exception:
            pass
        await update.callback_query.message.chat.send_message(text, reply_markup=reply_markup, parse_mode="Markdown")

# HÀM TỰ ĐỘNG HỦY ĐƠN SAU 5 PHÚT (300 GIÂY)
async def auto_cancel_order(context: ContextTypes.DEFAULT_TYPE, order_code: str, chat_id: int, message_id: int):
    await asyncio.sleep(300)
    order = PENDING_ORDERS.get(order_code)
    if order and order["status"] == "pending":
        order["status"] = "expired"
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏰ **Đơn hàng #{order_code} đã tự động hủy** do quá 5 phút chưa nhận được thanh toán.",
                parse_mode="Markdown"
            )
            expired_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Đơn hàng đã hết hạn", callback_data="none")]])
            await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=expired_kb)
        except Exception:
            pass

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user

    if data == "none":
        await query.answer("⚠️ Đơn hàng này đã hết hạn!", show_alert=True)
        return

    if data == "main_menu":
        await query.answer()
        await start_command(update, context)
        return

    if data == "back_to_menu":
        await query.answer()
        await menu_command(update, context)
        return

    if data == "menu_profile":
        await query.answer()
        u_data = get_user_data(user.id)
        profile_text = (
            f"👤 **HỒ SƠ CÁ NHÂN**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"• **Họ tên:** {user.full_name}\n"
            f"• **ID Telegram:** `{user.id}`\n"
            f"• **Username:** @{user.username if user.username else 'Chưa có'}\n"
            f"• **Số dư ví:** `{u_data['balance']:,} VNĐ`\n"
            f"• **Đã mua:** `{len(u_data['history'])} đơn hàng`"
        )
        kb = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="main_menu")]]
        await query.message.edit_text(profile_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data == "menu_history":
        await query.answer()
        u_data = get_user_data(user.id)
        history = u_data.get("history", [])
        if not history:
            hist_text = "🛡️ **LỊCH SỬ MUA HÀNG:**\n━━━━━━━━━━━━━━━━━━\nBạn chưa có giao dịch nào trên hệ thống."
        else:
            hist_text = "🛡️ **LỊCH SỬ MUA HÀNG (10 đơn gần nhất):**\n━━━━━━━━━━━━━━━━━━\n"
            for h in history[-10:]:
                hist_text += f"• `{h['order_code']}` - {h['product']} (-{h['amount']:,}đ)\n"
        kb = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="main_menu")]]
        await query.message.edit_text(hist_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data == "menu_wallet":
        await query.answer()
        u_data = get_user_data(user.id)
        wallet_text = (
            f"👛 **QUẢN LÝ VÍ TIỀN**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 **Số dư hiện tại:** `{u_data['balance']:,} VNĐ`\n\n"
            f"💡 **Hướng dẫn nạp tiền tự động 24/7:**\n"
            f"Chuyển khoản qua MB Bank với cú pháp nội dung CK:\n"
            f"`NAPVI {user.id}`\n\n"
            f"💳 **STK:** `{ACCOUNT_NO}`\n"
            f"👤 **Chủ TK:** {ACCOUNT_NAME}"
        )
        kb = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="main_menu")]]
        await query.message.edit_text(wallet_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data == "menu_api":
        await query.answer()
        api_text = (
            f"🔗 **HỆ THỐNG API DÀNH CHO RESELLER**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Bạn muốn kết nối API để bán lại tài khoản trên website hoặc bot riêng của bạn?\n"
            f"👉 Vui lòng liên hệ trực tiếp Quản Trị Viên để nhận tài liệu API và Key cấp độ đại lý uy tín!\n\n"
            f"💬 **Hỗ trợ API:** {ADMIN_CONTACT_LINK}"
        )
        kb = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="main_menu")]]
        await query.message.edit_text(api_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("buy|"):
        prod_key = data.split("|", 1)[1]
        product = PRODUCTS.get(prod_key)
        if not product or get_item_stock(product) <= 0:
            await query.answer("⚠️ Sản phẩm này hiện đã hết hàng!", show_alert=True)
            return
            
        await query.answer("⏳ Đang tạo hóa đơn...")
        order_code = f"DH{random.randint(10000, 99999)}"
        amount = product["price"]
        std_icon, _ = get_product_icon_and_logo(prod_key, product["name"])
        
        PENDING_ORDERS[order_code] = {
            "user_id": user.id,
            "username": f"@{user.username}" if user.username else user.full_name,
            "prod_key": prod_key,
            "amount": amount,
            "status": "pending"
        }
        
        caption = (
            f"🧾 **HÓA ĐƠN SHOPTAIKHOAN SUNLI: #{order_code}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{std_icon} **Sản phẩm:** {product['name']}\n"
            f"💰 **Tổng tiền:** `{amount:,} VNĐ`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏦 **MB Bank** | STK: `{ACCOUNT_NO}`\n"
            f"💬 **Nội dung CK:** `{order_code}`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ **LƯU Ý:** Đơn hàng sẽ tự động hủy sau **5 phút** nếu chưa thanh toán!\n"
            f"👉 Quét mã QR hoặc CK đúng nội dung, sau đó bấm nút bên dưới!"
        )
        keyboard = [
            [InlineKeyboardButton("✅ Tôi đã chuyển khoản", callback_data=f"paid|{order_code}")],
            [InlineKeyboardButton("🔙 Quay lại Menu", callback_data="main_menu")]
        ]
        qr_url = f"https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-compact2.png?amount={amount}&addInfo={quote(order_code)}&accountName={quote(ACCOUNT_NAME)}"
        try:
            qr_bytes = download_qr_image(qr_url)
            sent_msg = await query.message.chat.send_photo(photo=qr_bytes, caption=caption, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            await query.message.delete()
            context.application.create_task(auto_cancel_order(context, order_code, user.id, sent_msg.message_id))
        except Exception:
            sent_msg = await query.message.chat.send_message(text=caption + f"\n\n🔗 QR: {qr_url}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            await query.message.delete()
            context.application.create_task(auto_cancel_order(context, order_code, user.id, sent_msg.message_id))

    elif data.startswith("paid|"):
        order_code = data.split("|", 1)[1]
        order = PENDING_ORDERS.get(order_code)
        if not order:
            await query.answer("⚠️ Đơn không tồn tại!", show_alert=True)
            return
        if order["status"] == "expired":
            await query.answer("❌ Đơn hàng này đã quá 5 phút và đã bị hủy tự động!", show_alert=True)
            return
        if order["status"] == "notified":
            await query.answer("⏳ Đang chờ QTV duyệt!", show_alert=True)
            return
        order["status"] = "notified"
        product = PRODUCTS[order["prod_key"]]
        await query.answer("✅ Đã gửi yêu cầu xác nhận!")
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏳ Đang chờ QTV xác nhận...", callback_data="none")]]))
        
        admin_text = (
            f"🔔 **ĐƠN HÀNG MỚI - SHOPTAIKHOAN SUNLI!**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **Mã đơn:** `{order_code}`\n"
            f"👤 **Khách:** {order['username']} (`{order['user_id']}`)\n"
            f"📦 **Mua:** {product['name']}\n"
            f"💰 **Số tiền:** `{order['amount']:,} VNĐ`\n"
            f"💬 **Nội dung CK:** `{order_code}`"
        )
        admin_kb = [[
            InlineKeyboardButton("✅ Duyệt & Giao Ngay", callback_data=f"approve|{order_code}"),
            InlineKeyboardButton("❌ Từ chối", callback_data=f"reject|{order_code}")
        ]]
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(admin_kb))

    elif data.startswith("approve|"):
        if not is_admin(update):
            await query.answer("⛔ Bạn không phải QTV!", show_alert=True)
            return
        order_code = data.split("|", 1)[1]
        order = PENDING_ORDERS.get(order_code)
        if not order or order["status"] == "completed":
            await query.answer("⚠️ Đơn này đã xử lý rồi!", show_alert=True)
            return
        product = PRODUCTS[order["prod_key"]]
        
        if product.get("source") == "api":
            sup_key = product.get("supplier", "canboso")
            sup_name = SUPPLIERS.get(sup_key, {}).get("name", sup_key)
            ok, api_resp = purchase_from_api(sup_key, product["api_id"], quantity=1)
            if not ok:
                await query.answer(f"❌ Lỗi mua từ {sup_name}!", show_alert=True)
                await query.message.reply_text(f"⚠️ **Lỗi xuất hàng từ {sup_name}:**\n`{api_resp}`", parse_mode="Markdown")
                return
            formatted_account = format_account_delivery(api_resp)
        else:
            raw_stock = pop_stock_item(product["file"])
            if not raw_stock:
                await query.answer("❌ Kho .txt đã hết hàng!", show_alert=True)
                return
            formatted_account = format_account_delivery(raw_stock)

        order["status"] = "completed"
        add_user_history(order["user_id"], order_code, product["name"], order["amount"])
        
        customer_msg = (
            f"🎉 **GIAO DỊCH THÀNH CÔNG - ĐƠN #{order_code}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📦 **Sản phẩm:** {product['name']}\n"
            f"💰 **Thanh toán:** `{order['amount']:,} VNĐ`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔑 **THÔNG TIN TÀI KHOẢN CỦA BẠN:**\n"
            f"*(Chạm trực tiếp vào chữ để copy)*\n\n"
            f"{formatted_account}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💖 *Cảm ơn bạn đã tin tưởng **SHOPTAIKHOAN SUNLI**!*\n"
            f"📢 *Kênh thông báo: {USER_CHANNEL_LINK}*"
        )
        await context.bot.send_message(chat_id=order["user_id"], text=customer_msg, parse_mode="Markdown")
        await query.edit_message_text(text=query.message.text + f"\n\n✅ **ĐÃ DUYỆT:** {user.full_name}\n📤 **Đã xuất:**\n{formatted_account}", parse_mode="Markdown")
        await query.answer("🎉 Giao hàng thành công!")

        if USER_CHANNEL_ID:
            try:
                masked_user = str(order["user_id"])[:4] + "****"
                public_msg = (
                    f"🎉 **ĐƠN HÀNG THÀNH CÔNG (#{order_code})**\n"
                    f"🏪 **Hệ thống:** SHOPTAIKHOAN SUNLI\n"
                    f"👤 **Khách:** ID `{masked_user}`\n"
                    f"🛒 **Mua:** {product['name']}\n"
                    f"💰 **Thanh toán:** `{order['amount']:,} VNĐ` (Tự động ⚡)\n"
                    f"👉 Mua ngay tại Bot: @{context.bot.username}"
                )
                await context.bot.send_message(chat_id=USER_CHANNEL_ID, text=public_msg, parse_mode="Markdown")
            except Exception as e:
                print(f"⚠️ Lỗi đăng kênh: {e}")

    elif data.startswith("reject|"):
        if not is_admin(update):
            return
        order_code = data.split("|", 1)[1]
        order = PENDING_ORDERS.get(order_code)
        if order:
            order["status"] = "rejected"
            await context.bot.send_message(chat_id=order["user_id"], text=f"❌ **Đơn hàng #{order_code} đã bị hủy** do không nhận được thanh toán.", parse_mode="Markdown")
            await query.edit_message_text(text=query.message.text + f"\n\n❌ **ĐÃ TỪ CHỐI BỞI:** {user.full_name}", parse_mode="Markdown")
            await query.answer("Đã từ chối.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("qtv", admin_help_command))
    app.add_handler(CommandHandler("kho", check_stock_command))
    app.add_handler(CommandHandler("doigia", change_price_command))
    app.add_handler(CommandHandler("setlogo", set_logo_command))
    app.add_handler(CommandHandler("dslogo", list_logos_command))
    app.add_handler(CommandHandler("xoalogo", delete_logo_command))
    app.add_handler(CommandHandler("layid", get_emoji_id_command))
    app.add_handler(CommandHandler("themkho", add_stock_command))
    app.add_handler(CommandHandler("themsanpham", add_product_command))
    app.add_handler(CommandHandler("xoasanpham", delete_product_command))
    app.add_handler(CommandHandler("api", test_api_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("🚀 Bot Bán Hàng SHOPTAIKHOAN SUNLI (Hỗ trợ Full Custom Emoji Telegram Premium) Đang Chạy...")
    app.run_polling()
