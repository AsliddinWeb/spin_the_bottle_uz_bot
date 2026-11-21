# Ubuntu serverga o'rnatish

Talab: Ubuntu 24.04 (Python 3.12+ kerak), nginx, domen/subdomen.
Bot polling rejimida ishlaydi: bitta token bilan faqat BITTA nusxa ishlashi mumkin. Serverda ishga tushirishdan oldin kompyuterdagi serverni (run.sh) to'xtating.

## 1. Band portlarni tekshirish
    ss -ltnp | grep -E ':(8010|8011|8012)\b' || echo "8010 bo'sh"
Band bo'lsa deploy/spinbot.service dagi --port va nginx dagi proxy_pass ni bo'sh portga almashtiring.

## 2. Kod va muhit
    sudo adduser --system --group --home /opt/spinbot spinbot
    sudo git clone https://github.com/<user>/<repo>.git /opt/spinbot
    cd /opt/spinbot
    sudo -u spinbot python3 -m venv .venv
    sudo -u spinbot .venv/bin/pip install -r requirements.txt
    sudo -u spinbot cp .env.example .env
    sudo -u spinbot nano .env      # BOT_TOKEN, WEBAPP_URL=https://spin.example.com, ADMIN_IDS, SUPPORT, PAY_INFO, PRICES; DEV_MODE yozilmasin
    sudo chmod 600 /opt/spinbot/.env

## 3. Servis
    sudo cp deploy/spinbot.service /etc/systemd/system/
    sudo systemctl daemon-reload && sudo systemctl enable --now spinbot
    systemctl status spinbot --no-pager ; journalctl -u spinbot -f

## 4. nginx + HTTPS
    sudo cp deploy/nginx-spinbot.conf /etc/nginx/sites-available/spinbot   # server_name ni o'zgartiring
    sudo ln -s /etc/nginx/sites-available/spinbot /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl reload nginx
    sudo certbot --nginx -d spin.example.com

## 5. Yangilash
    cd /opt/spinbot && sudo -u spinbot git pull && sudo -u spinbot .venv/bin/pip install -r requirements.txt && sudo systemctl restart spinbot

## Ma'lumotlar
Baza va rasmlar /opt/spinbot ichida (spin.db, uploads/, backups/), git'ga kirmaydi. Zaxira avtomatik (har 24 soat, oxirgi 14 ta).
Tiklash: systemctl stop spinbot; sudo -u spinbot .venv/bin/python restore_backup.py latest; systemctl start spinbot
