"""Musiqa va video alohida: rejim treklarga yoziladi, ro'yxatlar rejim bo'yicha, Telegram pleylist endpointlari. Dev server :8001 kerak."""
import asyncio, json, urllib.request, urllib.error
import websockets
B = "localhost:8001"; fails = []; passed = 0


def call(path, uid, body=None):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST" if body is not None else "GET")
    try:
        return 200, json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e:
        return e.code, {}


def ok(name, cond, info=""):
    global passed
    if cond: passed += 1
    else: fails.append(f"{name} {info}")


async def main():
    call("/api/profile", 90, {"name": "M", "birth": "2000-01-01", "gender": "m", "lang": "uz"})
    ws = await websockets.connect(f"ws://{B}/ws?init=dev:90")
    state = {}

    async def rd():
        async for raw in ws:
            m = json.loads(raw)
            if m.get("t") == "state": state["s"] = m
    asyncio.create_task(rd())
    await ws.send(json.dumps({"t": "join", "table": 7})); await asyncio.sleep(1)
    send = lambda d: ws.send(json.dumps(d))
    await send({"t": "gift", "to": 0, "gift": "music_now", "url": "https://youtu.be/aaaaaaaaaaa", "mode": "video"}); await asyncio.sleep(1.5)
    await send({"t": "gift", "to": 0, "gift": "music_queue", "url": "https://youtu.be/bbbbbbbbbbb"}); await asyncio.sleep(1.5)
    await send({"t": "gift", "to": 0, "gift": "music_queue", "url": "tg:nonexistent"}); await asyncio.sleep(1)
    st = json.dumps(state.get("s", {}))
    ok("video trek holatda", '"mode": "video"' in st and "aaaaaaaaaaa" in st, st[:200])
    v = call("/api/music/popular?mode=video", 90)[1]; a = call("/api/music/popular?mode=audio", 90)[1]
    ok("video ro'yxatida faqat video", [x["vid"] for x in v] == ["aaaaaaaaaaa"], v)
    ok("musiqa ro'yxatida faqat musiqa", [x["vid"] for x in a] == ["bbbbbbbbbbb"], a)
    hv = call("/api/music/history?mode=video", 90)[1]; ha = call("/api/music/history?mode=audio", 90)[1]
    ok("tarix rejim bo'yicha", [x["vid"] for x in hv] == ["aaaaaaaaaaa"] and [x["vid"] for x in ha] == ["bbbbbbbbbbb"], (hv, ha))
    ok("noma'lum tg trek rad (xabar ro'yxatda yo'q)", "nonexistent" not in st)
    c, r = call("/api/music/tg", 90); ok("tg pleylist ro'yxati (botsiz bo'sh)", c == 200 and r == [], r)
    try:
        urllib.request.urlopen(f"http://{B}/api/tgaudio/abc"); ok("init yo'q = 401", False)
    except urllib.error.HTTPError as e:
        ok("init yo'q = 401", e.code == 401, e.code)
    try:
        urllib.request.urlopen(f"http://{B}/api/tgaudio/abc?init=dev:90"); ok("fayl yo'q = 404", False)
    except urllib.error.HTTPError as e:
        ok("fayl yo'q = 404", e.code == 404, e.code)
    await ws.close()

asyncio.run(main())
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)
