# Ubuntu serverga o'rnatish (Docker)

Talab: Docker + docker compose, nginx, domen (spin.neonsoft.uz).
Bot polling rejimida ishlaydi: bitta token bilan faqat BITTA nusxa ishlashi mumkin. Avval kompyuterdagi serverni to'xtating.

## 1. Kod
    git clone https://github.com/AsliddinWeb/spin_the_bottle_uz_bot.git /opt/spinbot
    cd /opt/spinbot
    cp .env.example .env && nano .env   # BOT_TOKEN, WEBAPP_URL=https://spin.neonsoft.uz, ADMIN_IDS, SUPPORT, PAY_INFO, PRICES; DEV_MODE yozilmasin
    chmod 600 .env

## 2. Ishga tushirish
    docker compose up -d --build
    docker compose logs -f spinbot
Konteyner faqat 127.0.0.1:8010 da tinglaydi (tashqaridan ochiq emas). Port band bo'lsa docker-compose.yml dagi chap raqamni o'zgartiring
(va nginx dagi proxy_pass ni ham).

## 3. nginx + HTTPS
    cp deploy/nginx-spinbot.conf /etc/nginx/sites-available/spinbot
    ln -s /etc/nginx/sites-available/spinbot /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx
    certbot --nginx -d spin.neonsoft.uz -d www.spin.neonsoft.uz
(`map $http_upgrade $connection_upgrade` nginx.conf http{} ichida bo'lishi kerak, WebSocket uchun.)

## 4. Yangilash
    cd /opt/spinbot && git pull && docker compose up -d --build

## Ma'lumotlar
Hammasi /opt/spinbot ichida, git'ga kirmaydi: data/spin.db, uploads/, backups/. Zaxira avtomatik (har 24 soat, oxirgi 14 ta).
Tiklash: docker compose stop; docker compose run --rm spinbot python restore_backup.py latest; docker compose start
