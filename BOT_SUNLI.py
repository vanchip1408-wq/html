import os
import json
import random
import uuid
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

# CẤU HÌNH ĐẤU NỐI API NGUỒN (CANBOSO.COM)
API_BASE_URL = "https://canboso.com"
API_KEY = "tgb_c4df682ad0774092b11d6e6507af47d9bc7b240233c5bb97"
PROFIT_MARGIN = 10000

# FILE LƯU TRỮ DỮ LIỆU VĨNH VIỄN
BLOCKED_FILE = "sanpham_da_xoa.json"
CUSTOM_PRICES_FILE = "gia_tuy_chinh.json"
CUSTOM_LOGOS_FILE = "logo_san_pham.json"

DEFAULT_BLOCKED = {
    "api_6a9e637c4f6e4dbc77f68033",
    "api_6add9d0cbe0925eeb509e9c7"
}

# THÔNG TIN NGÂN HÀNG NHẬN TIỀN VIETQR
BANK_ID = "MB"
ACCOUNT_NO = "0979770049"
ACCOUNT_NAME = "BUI VAN MINH"

PRODUCTS = {
    "canva": {
        "name": "Canva Pro 1 Năm",
        "price": 30000,
        "desc": "Nâng cấp chính chủ, bảo hành full thời gian sử dụng.",
        "file": "kho_canva.txt",
        "source": "local"
    }
}

PENDING_ORDERS = {}
# =============================================================

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
    if not os.path.exists(CUSTOM_LOGOS_FILE):
        return {}
    try:
        with open(CUSTOM_LOGOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_custom_logo(keyword, emoji_id):
    logos = load_custom_logos()
    logos[keyword.lower()] = str(emoji_id).strip()
    with open(CUSTOM_LOGOS_FILE, "w", encoding="utf-8") as f:
        json.dump(logos, f, ensure_ascii=False, indent=2)

def get_product_icon_and_logo(prod_key, prod_name):
    name_lower = prod_name.lower()
    key_lower = prod_key.lower()
    custom_logos = load_custom_logos()
    
    custom_emoji_id = custom_logos.get(key_lower)
    if not custom_emoji_id:
        for kw, eid in custom_logos.items():
            if kw in name_lower:
                custom_emoji_id = eid
                break
                
    std_icon = "💎"
    brand_icons = {
        "canva": "🎨", "capcut": "🎬", "gemini": "✨", "gpt": "🤖", "chatgpt": "🤖",
        "claude": "🧠", "deepseek": "🐳", "grok": "🌌", "netflix": "🍿", "youtube": "▶️",
        "spotify": "🎵", "suno": "🎼", "adobe": "🅰️", "figma": "📐", "vpn": "🛡️"
    }
    for brand_kw, icon in brand_icons.items():
        if brand_kw in name_lower or brand_kw in key_lower:
            std_icon = icon
            break
            
    return std_icon, custom_emoji_id

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

def call_supplier_api(endpoint, method="GET", payload=None, extra_headers=None):
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
        "x-api-key": API_KEY,
        "Authorization": f"Bearer {API_KEY}"
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

def sync_api_products():
    try:
        blocked_keys = load_blocked_keys()
        custom_prices = load_custom_prices()
        
        for b_key in list(PRODUCTS.keys()):
            if b_key.lower() in blocked_keys:
                del PRODUCTS[b_key]

        data, err = call_supplier_api("/api/v2/telegram-buyer/products", method="GET")
        if err or not data:
            apply_saved_prices()
            return False, err, data

        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for k in ["data", "products", "items", "result"]:
                if k in data and isinstance(data[k], list):
                    items = data[k]
                    break

        count = 0
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
                key = f"api_{str(prod_id)[:40]}".lower()
                if key in blocked_keys or str(prod_id).lower() in blocked_keys:
                    continue

                final_price = custom_prices.get(key, base_price + PROFIT_MARGIN)

                PRODUCTS[key] = {
                    "name": name,
                    "base_price": base_price,
                    "price": final_price,
                    "desc": desc_text,
                    "stock": stock,
                    "api_id": prod_id,
                    "source": "api"
                }
                count += 1
                
        apply_saved_prices()
        return True, f"Đã đồng bộ {count} sản phẩm từ API!", data
    except Exception as e:
        return False, str(e), None

def purchase_from_api(api_prod_id, quantity=1):
    payload = {"productId": api_prod_id, "product_id": api_prod_id, "quantity": quantity, "amount": quantity}
    # Tự động sinh Idempotency-Key hợp lệ (dùng uuid4) để vượt qua lỗi yêu cầu từ canboso.com
    idempotency_key = str(uuid.uuid4())
    headers = {"Idempotency-Key": idempotency_key}
    
    data, err = call_supplier_api("/api/v2/telegram-buyer/purchase", method="POST", payload=payload, extra_headers=headers)
    if err:
        return False, f"Lỗi gọi API mua hàng: {err}"
    return True, data

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

async def post_init(application):
    init_stock_files()
    sync_api_products()
    commands = [
        BotCommand("start", "Để bắt đầu sử dụng bot"),
        BotCommand("menu", "Để xem những sản phẩm đang bán"),
        BotCommand("qtv", "Xem danh sách lệnh quản trị"),
    ]
    await application.bot.set_my_commands(commands)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "bạn"
    welcome_text = (
        f"🌟 **CHÀO MỪNG ĐẾN VỚI SHOPTAIKHOAN SUNLI** 🌟\n"
        f"👋 Xin chào **{user_name}**, chúc bạn một ngày tốt lành!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🚀 **Hệ thống bán tài khoản Premium tự động 24/7:**\n"
        f"• ⚡ **Giao hàng siêu tốc:** Nhận tài khoản ngay lập tức.\n"
        f"• 🛡️ **Bảo hành uy tín:** Hỗ trợ kỹ thuật & đổi trả nhanh chóng.\n"
        f"• 💰 **Giá cực hạt dẻ:** Đa dạng sản phẩm học tập, làm việc & giải trí.\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👇 **Bấm vào nút bên dưới để xem bảng giá và mua hàng ngay nhé!**"
    )
    if is_admin(update):
        welcome_text += "\n\n👑 *[QTV] Gõ lệnh `/qtv` để mở bảng quản lý shop.*"
        
    keyboard = [
        [InlineKeyboardButton("🛒 Xem Menu Sản Phẩm", callback_data="back_to_menu")],
        [
            InlineKeyboardButton("📢 Kênh Uy Tín", url=USER_CHANNEL_LINK),
            InlineKeyboardButton("💬 Hỗ Trợ QTV", url=ADMIN_CONTACT_LINK)
        ]
    ]
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    help_text = (
        "👑 **BẢNG ĐIỀU KHIỂN - SHOPTAIKHOAN SUNLI:**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "• `/kho` : Xem mã sản phẩm, giá bán & tồn kho\n"
        "• `/doigia <mã> <giá_mới>` : Đổi giá bán của sản phẩm\n"
        "• `/setlogo <từ_khóa> <emoji_logo>` : Gắn Logo Custom Emoji lên nút bấm\n"
        "• `/themkho <mã> <tài_khoản>` : Nạp hàng vào kho .txt\n"
        "• `/themsanpham <mã> | <tên> | <giá> | <mô_tả>` : Thêm sản phẩm mới\n"
        "• `/xoasanpham <mã>` : Xóa/Ẩn sản phẩm vĩnh viễn\n"
        "• `/api` : Đồng bộ lại sản phẩm từ canboso.com"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def set_logo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    parts = update.message.text.split()
    if len(parts) < 2:
        await update.message.reply_text(
            "🎨 **CÁCH GẮN LOGO THƯƠNG HIỆU LÊN NÚT BẤM:**\n"
            "Gõ: `/setlogo <từ_khóa> <icon_logo_Premium>` hoặc `/setlogo <từ_khóa> <custom_emoji_id>`",
            parse_mode="Markdown"
        )
        return
        
    keyword = parts[1].strip().lower()
    custom_emoji_id = None
    
    if update.message.entities:
        for ent in update.message.entities:
            if ent.type == "custom_emoji" and ent.custom_emoji_id:
                custom_emoji_id = ent.custom_emoji_id
                break
                
    if not custom_emoji_id and len(parts) >= 3 and parts[2].isdigit():
        custom_emoji_id = parts[2].strip()
        
    if not custom_emoji_id:
        await update.message.reply_text("⚠️ Không tìm thấy Custom Emoji Logo trong tin nhắn của bạn!", parse_mode="Markdown")
        return
        
    save_custom_logo(keyword, custom_emoji_id)
    await update.message.reply_text(f"✅ Đã gắn Logo thành công cho từ khóa `{keyword}`!", parse_mode="Markdown")

async def check_stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    sync_api_products()
    msg = "📦 **DANH SÁCH SẢN PHẨM & BẢNG GIÁ HIỆN TẠI:**\n━━━━━━━━━━━━━━━━━━\n"
    for key, item in PRODUCTS.items():
        count = get_item_stock(item)
        std_icon, _ = get_product_icon_and_logo(key, item['name'])
        src = f"API - Giá gốc: {item.get('base_price', 0):,}đ" if item.get("source") == "api" else "Kho .txt"
        msg += (
            f"{std_icon} **{item['name']}**\n"
            f"  Mã: `{key}`\n"
            f"  Giá bán: **`{item['price']:,}đ`** ({src}) | Kho: **{count}**\n\n"
        )
    msg += "💡 *Đổi giá:* `/doigia <mã> <giá_mới>`"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def change_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    parts = update.message.text.split()
    if len(parts) < 3:
        await update.message.reply_text("⚠️ Cách dùng: `/doigia <mã_sản_phẩm> <giá_tiền_mới>`", parse_mode="Markdown")
        return
        
    code = parts[1].strip().lower()
    price_str = parts[2].strip()
    
    if code not in PRODUCTS:
        await update.message.reply_text(f"❌ Không tìm thấy mã `{code}`!", parse_mode="Markdown")
        return
        
    try:
        new_price = int(''.join(filter(str.isdigit, price_str)))
    except ValueError:
        await update.message.reply_text("❌ Giá tiền phải là số!", parse_mode="Markdown")
        return
        
    old_price = PRODUCTS[code]["price"]
    PRODUCTS[code]["price"] = new_price
    save_custom_price(code, new_price)
    
    await update.message.reply_text(
        f"✅ **Đổi giá thành công!**\n📦 {PRODUCTS[code]['name']}\n💰 `{old_price:,}đ` ➡️ **`{new_price:,}đ`**",
        parse_mode="Markdown"
    )

async def add_product_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    text = update.message.text.replace("/themsanpham", "").strip()
    parts = [p.strip() for p in text.split("|")]
    
    if len(parts) < 4:
        await update.message.reply_text("⚠️ Cách dùng: `/themsanpham <mã> | <tên_sp> | <giá> | <mô_tả>`", parse_mode="Markdown")
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
        await update.message.reply_text("⚠️ Nhập mã cần xóa: `/xoasanpham <mã>`", parse_mode="Markdown")
        return
    save_blocked_keys(codes)
    for code in codes:
        if code in PRODUCTS:
            del PRODUCTS[code]
    await update.message.reply_text("✅ Đã xóa & chặn vĩnh viễn thành công!", parse_mode="Markdown")

async def add_stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    text = update.message.text
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await update.message.reply_text("⚠️ Cách dùng: `/themkho <mã_sp> <tài_khoản>`", parse_mode="Markdown")
        return
    prod_key = parts[1].lower()
    raw_accounts = parts[2].strip().split("\n")
    if prod_key not in PRODUCTS:
        await update.message.reply_text("❌ Mã sản phẩm không tồn tại!", parse_mode="Markdown")
        return
    product = PRODUCTS[prod_key]
    if product.get("source") == "api":
        await update.message.reply_text("⚠️ Sản phẩm lấy từ API không cần nạp kho .txt!", parse_mode="Markdown")
        return
    with open(product["file"], "a", encoding="utf-8") as f:
        for acc in raw_accounts:
            if acc.strip():
                f.write(acc.strip() + "\n")
    total = get_item_stock(product)
    await update.message.reply_text(f"✅ Đã nạp thêm vào **{product['name']}**! Tổng kho: **{total}**", parse_mode="Markdown")

async def test_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    ok, msg, _ = sync_api_products()
    await update.message.reply_text(f"{'✅' if ok else '❌'} {msg}", parse_mode="Markdown")

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
        
        if stock > 0:
            prefix = "" if custom_emoji_id else f"{std_icon} "
            btn_text = f"{prefix}{item['name']} ({price_str}) | Còn: {stock}"
        else:
            btn_text = f"❌ {item['name']} ({price_str}) | HẾT HÀNG"
            custom_emoji_id = None
            
        if custom_emoji_id:
            try:
                btn = InlineKeyboardButton(btn_text, callback_data=f"buy|{key}", api_kwargs={"icon_custom_emoji_id": str(custom_emoji_id)})
            except Exception:
                btn = InlineKeyboardButton(f"{std_icon} {item['name']} ({price_str}) | Còn: {stock}", callback_data=f"buy|{key}")
        else:
            btn = InlineKeyboardButton(btn_text, callback_data=f"buy|{key}")
            
        keyboard.append([btn])
    
    keyboard.append([
        InlineKeyboardButton("📢 Kênh Cộng Đồng", url=USER_CHANNEL_LINK),
        InlineKeyboardButton("💬 Hỗ Trợ", url=ADMIN_CONTACT_LINK)
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "📋 **MENU SẢN PHẨM - SHOPTAIKHOAN SUNLI**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "*(Chạm trực tiếp vào sản phẩm bên dưới để mua tự động)*"
    )
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        try:
            await update.callback_query.message.delete()
        except Exception:
            pass
        await update.callback_query.message.chat.send_message(text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user

    if data == "back_to_menu":
        await query.answer()
        await menu_command(update, context)
        return

    if data.startswith("buy|"):
        prod_key = data.split("|", 1)[1]
        product = PRODUCTS.get(prod_key)
        
        if not product or get_item_stock(product) <= 0:
            await query.answer("⚠️ Sản phẩm này hiện đã hết hàng!", show_alert=True)
            return
            
        await query.answer("⏳ Đang tạo hóa đơn thanh toán...")
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
            f"📝 **Mô tả:** {product['desc']}\n"
            f"💰 **Tổng tiền:** `{amount:,} VNĐ`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏦 **Ngân hàng:** MB Bank\n"
            f"💳 **STK:** `{ACCOUNT_NO}`\n"
            f"👤 **Chủ TK:** {ACCOUNT_NAME}\n"
            f"💬 **Nội dung CK:** `{order_code}`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ **HƯỚNG DẪN:** Quét mã QR bên dưới hoặc chuyển khoản đúng số tiền và nội dung `{order_code}`, sau đó bấm nút **✅ Tôi đã chuyển khoản** bên dưới!"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Tôi đã chuyển khoản", callback_data=f"paid|{order_code}")],
            [InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_to_menu")]
        ]
        
        qr_url = (
            f"https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-compact2.png"
            f"?amount={amount}&addInfo={quote(order_code)}&accountName={quote(ACCOUNT_NAME)}"
        )
        
        try:
            qr_bytes = download_qr_image(qr_url)
            await query.message.chat.send_photo(
                photo=qr_bytes,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await query.message.delete()
        except Exception:
            await query.message.chat.send_message(
                text=caption + f"\n\n🔗 **Link QR Thanh Toán:** {qr_url}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await query.message.delete()

    elif data.startswith("paid|"):
        order_code = data.split("|", 1)[1]
        order = PENDING_ORDERS.get(order_code)
        if not order:
            await query.answer("⚠️ Đơn hàng không tồn tại!", show_alert=True)
            return
        if order["status"] == "notified":
            await query.answer("⏳ Đang chờ QTV duyệt!", show_alert=True)
            return
        order["status"] = "notified"
        product = PRODUCTS[order["prod_key"]]
        await query.answer("✅ Đã gửi yêu cầu xác nhận!", show_alert=True)
        
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏳ Đang chờ QTV xác nhận thanh toán...", callback_data="none")]])
        )
        
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
            InlineKeyboardButton("✅ Duyệt & Giao Hàng Ngay", callback_data=f"approve|{order_code}"),
            InlineKeyboardButton("❌ Từ chối", callback_data=f"reject|{order_code}")
        ]]
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=admin_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(admin_kb)
        )

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
            ok, api_resp = purchase_from_api(product["api_id"], quantity=1)
            if not ok:
                await query.answer("❌ Lỗi mua từ API nguồn!", show_alert=True)
                await query.message.reply_text(f"⚠️ **Không thể xuất hàng từ canboso.com:**\n`{api_resp}`", parse_mode="Markdown")
                return
            if isinstance(api_resp, dict):
                account_data = api_resp.get("account") or api_resp.get("data") or api_resp.get("item") or json.dumps(api_resp, ensure_ascii=False)
            else:
                account_data = str(api_resp)
        else:
            account_data = pop_stock_item(product["file"])
            if not account_data:
                await query.answer("❌ Kho .txt đã hết hàng!", show_alert=True)
                return

        order["status"] = "completed"
        
        customer_msg = (
            f"🎉 **GIAO DỊCH THÀNH CÔNG - ĐƠN #{order_code}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📦 **Sản phẩm:** {product['name']}\n"
            f"🔑 **Thông tin tài khoản của bạn (Chạm để copy):**\n`{account_data}`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💖 *Cảm ơn bạn đã tin tưởng **SHOPTAIKHOAN SUNLI**!*\n"
            f"📢 *Kênh thông báo & bảo hành: {USER_CHANNEL_LINK}*"
        )
        await context.bot.send_message(chat_id=order["user_id"], text=customer_msg, parse_mode="Markdown")
        
        await query.edit_message_text(
            text=query.message.text + f"\n\n✅ **ĐÃ DUYỆT BỞI:** {user.full_name}\n📤 **Đã xuất:** `{account_data}`",
            parse_mode="Markdown"
        )
        await query.answer("🎉 Đã giao hàng thành công!")

        if USER_CHANNEL_ID:
            try:
                masked_user = str(order["user_id"])[:4] + "****"
                public_msg = (
                    f"🎉 **ĐƠN HÀNG THÀNH CÔNG (#{order_code})**\n"
                    f"🏪 **Hệ thống:** SHOPTAIKHOAN SUNLI\n"
                    f"👤 **Khách hàng:** ID `{masked_user}`\n"
                    f"🛒 **Vừa mua:** {product['name']}\n"
                    f"💰 **Thanh toán:** `{order['amount']:,} VNĐ` (Giao tự động ⚡)\n"
                    f"👉 Mua ngay tại Bot: @{context.bot.username}"
                )
                await context.bot.send_message(chat_id=USER_CHANNEL_ID, text=public_msg, parse_mode="Markdown")
            except Exception as e:
                print(f"⚠️ Không thể đăng bài lên kênh thông báo: {e}")

    elif data.startswith("reject|"):
        if not is_admin(update):
            return
        order_code = data.split("|", 1)[1]
        order = PENDING_ORDERS.get(order_code)
        if order:
            order["status"] = "rejected"
            await context.bot.send_message(
                chat_id=order["user_id"],
                text=f"❌ **Đơn hàng #{order_code} đã bị hủy** do hệ thống chưa nhận được thanh toán.",
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                text=query.message.text + f"\n\n❌ **ĐÃ TỪ CHỐI BỞI:** {user.full_name}",
                parse_mode="Markdown"
            )
            await query.answer("Đã từ chối đơn hàng.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("qtv", admin_help_command))
    app.add_handler(CommandHandler("kho", check_stock_command))
    app.add_handler(CommandHandler("doigia", change_price_command))
    app.add_handler(CommandHandler("setlogo", set_logo_command))
    app.add_handler(CommandHandler("themkho", add_stock_command))
    app.add_handler(CommandHandler("themsanpham", add_product_command))
    app.add_handler(CommandHandler("xoasanpham", delete_product_command))
    app.add_handler(CommandHandler("api", test_api_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("🚀 Bot Bán Hàng SHOPTAIKHOAN SUNLI (Đã Fix Lỗi Idempotency-Key) Đang Chạy...")
    app.run_polling()
