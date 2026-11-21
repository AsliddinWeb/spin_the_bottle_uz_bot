# Ubuntu serverga o'rnatish

Talab: Ubuntu 24.04 (Python 3.12+ kerak), nginx, domen/subdomen.
Bot polling rejimida ishlaydi: bitta token bilan faqat BITTA nusxa ishlashi mumkin. Serverda ishga tushirishdan oldin kompyuterdagi serverni (run.sh) to'xtating.

## 1. Band portlarni tekshirish
    ss -ltnp | grep -E ':(8010|8011|8012)\b' || echo "8010 bo'sh"
Band bo'lsa deploy/spinbot.service dagi --port va nginx dagi proxy_pass ni bo'sh portga almashtiring.

## 2. Kod va muhit
    git clone https://github.com/<user>/<repo>.git /opt/spinbot
    cd /opt/spinbot
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    cp .env.example .env
    nano .env      # BOT_TOKEN, WEBAPP_URL=https://spin.neonsoft.uz, ADMIN_IDS, SUPPORT, PAY_INFO, PRICES; DEV_MODE yozilmasin
    chmod 600 /opt/spinbot/.env

## 3. Servis
    cp deploy/spinbot.service /etc/systemd/system/
    systemctl daemon-reload && systemctl enable --now spinbot
    systemctl status spinbot --no-pager ; journalctl -u spinbot -f

## 4. nginx + HTTPS
    cp deploy/nginx-spinbot.conf /etc/nginx/sites-available/spinbot   # server_name ni o'zgartiring
    ln -s /etc/nginx/sites-available/spinbot /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx
    certbot --nginx -d spin.neonsoft.uz -d www.spin.neonsoft.uz

## 5. Yangilash
    cd /opt/spinbot && git pull && .venv/bin/pip install -r requirements.txt && systemctl restart spinbot

## Ma'lumotlar
Baza va rasmlar /opt/spinbot ichida (spin.db, uploads/, backups/), git'ga kirmaydi. Zaxira avtomatik (har 24 soat, oxirgi 14 ta).
Tiklash: systemctl stop spinbot; .venv/bin/python restore_backup.py latest; systemctl start spinbot
