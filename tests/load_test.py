"""Load test: N bots play the real game over WebSockets (join random tables, spin, answer kiss prompts, chat, send gifts).
Measures chat round-trip latency (own message echoed back by the server), REST latency (/api/me) and the server process' CPU / RAM.

    # server (own shell, high fd limit, temp DB, no Telegram):
    ulimit -n 20000; BOT_TOKEN= DEV_MODE=1 DB_PATH=/tmp/load.db PORT=8001 .venv/bin/uvicorn app.main:app --port 8001 --ws-ping-interval 15 --ws-ping-timeout 15
    # test:
    ulimit -n 20000; .venv/bin/python tests/load_test.py 300 60 <server pid>
"""
import asyncio, json, os, random, statistics, subprocess, sys, time, urllib.request

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
SECS = int(sys.argv[2]) if len(sys.argv) > 2 else 60
PID = int(sys.argv[3]) if len(sys.argv) > 3 else 0
HOST = "localhost:8001"
BASE = 100000
import websockets

RATE = float(os.environ.get("RATINGS_PER_S", "0"))   # extra heavy REST calls per second (ratings / tag task) from random players
lat_chat, lat_http, lat_heavy, errors = [], [], [], {"connect": 0, "dropped": 0, "http": 0}
rx = {"msgs": 0, "bytes": 0}
samples = []  # (t, cpu%, rss MB)


def post(path, uid, body):
    r = urllib.request.Request(f"http://{HOST}{path}", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST")
    return urllib.request.urlopen(r, timeout=30).read()


def get(path, uid):
    r = urllib.request.Request(f"http://{HOST}{path}", headers={"X-Init-Data": f"dev:{uid}"})
    return urllib.request.urlopen(r, timeout=30).read()


def cputime(pid):
    out = subprocess.run(["ps", "-o", "time=,rss=", "-p", str(pid)], capture_output=True, text=True).stdout.split()
    if len(out) < 2:
        return None, None
    t = out[0].split(":"); secs = float(t[-1]) + 60 * int(t[-2]) + (3600 * int(t[-3]) if len(t) > 2 else 0)
    return secs, int(out[1]) / 1024


async def monitor(stop):
    if not PID:
        return
    c0, _ = cputime(PID); w0 = time.time()
    while not stop.is_set():
        await asyncio.sleep(2)
        c1, rss = cputime(PID); w1 = time.time()
        if c1 is not None and c0 is not None:
            samples.append((w1, 100 * (c1 - c0) / (w1 - w0), rss))
        c0, w0 = c1, w1


async def http_probe(stop, uids):
    loop = asyncio.get_running_loop()
    while not stop.is_set():
        await asyncio.sleep(0.5)
        uid = random.choice(uids); t = time.perf_counter()
        try:
            await loop.run_in_executor(None, get, "/api/me", uid); lat_http.append((time.perf_counter() - t) * 1000)
        except Exception:
            errors["http"] += 1


async def heavy_probe(stop, uids):
    loop = asyncio.get_running_loop()
    while not stop.is_set() and RATE:
        await asyncio.sleep(1 / RATE)
        uid = random.choice(uids); path = random.choice(["/api/ratings/kisses", "/api/ratings/court", "/api/tagtask"]); t = time.perf_counter()
        async def one():
            try:
                await loop.run_in_executor(None, get, path, uid); lat_heavy.append((time.perf_counter() - t) * 1000)
            except Exception:
                errors["http"] += 1
        asyncio.create_task(one())


class Bot:
    def __init__(self, uid):
        self.uid, self.n, self.sent = uid, 0, {}
        self.table = None

    async def run(self, stop):
        try:
            ws = await websockets.connect(f"ws://{HOST}/ws?init=dev:{self.uid}", max_size=2 ** 22, ping_interval=None, open_timeout=30)
        except Exception:
            errors["connect"] += 1
            return
        self.ws = ws
        await ws.send(json.dumps({"t": "join", "table": "random"}))
        chat = asyncio.create_task(self.chatter(stop))
        try:
            async for raw in ws:
                rx["msgs"] += 1; rx["bytes"] += len(raw)
                m = json.loads(raw); t = m.get("t")
                if t == "state":
                    asyncio.create_task(self.react(m))
                elif t == "chat" and m.get("k") == "msg" and m.get("uid") == self.uid:
                    s = self.sent.pop(m.get("text"), None)
                    if s:
                        lat_chat.append((time.perf_counter() - s) * 1000)
                elif t == "left":
                    await ws.send(json.dumps({"t": "join", "table": "random"}))
                if stop.is_set():
                    break
        except Exception:
            if not stop.is_set():
                errors["dropped"] += 1
        finally:
            chat.cancel()
            try:
                await ws.close()
            except Exception:
                pass

    async def react(self, s):
        await asyncio.sleep(random.uniform(.2, 1.2))
        try:
            if s["phase"] == "spin_wait" and s["turn"] == self.uid:
                await self.ws.send(json.dumps({"t": "spin"}))
            elif s["phase"] == "ask_spinner" and s["turn"] == self.uid:
                await self.ws.send(json.dumps({"t": "decide", "v": random.random() < .7}))
            elif s["phase"] == "ask_target" and s["target"] == self.uid:
                await self.ws.send(json.dumps({"t": "decide", "v": random.random() < .6}))
        except Exception:
            pass

    async def chatter(self, stop):
        await asyncio.sleep(random.uniform(3, 12))
        while not stop.is_set():
            self.n += 1; text = f"hi {self.uid % 1000} n{self.n} {random.randint(100, 999)}"
            self.sent[text] = time.perf_counter()
            try:
                await self.ws.send(json.dumps({"t": "chat", "text": text}))
            except Exception:
                return
            await asyncio.sleep(random.uniform(8, 20))   # a lively table: one message per ~14 s per player


def pct(a, p):
    if not a:
        return 0
    a = sorted(a); return a[min(len(a) - 1, int(len(a) * p / 100))]


async def main():
    uids = [BASE + i for i in range(N)]
    loop = asyncio.get_running_loop(); t0 = time.time()
    # profiles (REST), parallel in a thread pool
    sem = asyncio.Semaphore(32)
    async def mk(u):
        async with sem:
            await loop.run_in_executor(None, post, "/api/profile", u, {"name": f"L{u % 100000}", "birth": "2000-01-01", "gender": "m" if u % 2 else "f", "lang": "ru"})
    await asyncio.gather(*(mk(u) for u in uids))
    t_prof = time.time() - t0
    stop = asyncio.Event(); bots = [Bot(u) for u in uids]
    mon = asyncio.create_task(monitor(stop)); probe = asyncio.create_task(http_probe(stop, uids)); hv = asyncio.create_task(heavy_probe(stop, uids))
    tasks = []
    t1 = time.time()
    for i in range(0, N, 25):               # ramp: 25 connections every 0.25 s
        tasks += [asyncio.create_task(b.run(stop)) for b in bots[i:i + 25]]
        await asyncio.sleep(.25)
    ramp = time.time() - t1
    await asyncio.sleep(3)
    start_msgs, start_bytes, t_s = rx["msgs"], rx["bytes"], time.time()
    lat_chat.clear(); lat_http.clear(); lat_heavy.clear(); samples.clear()
    await asyncio.sleep(SECS)
    dur = time.time() - t_s; msgs, byt = rx["msgs"] - start_msgs, rx["bytes"] - start_bytes
    stop.set()
    await asyncio.sleep(1)
    for t in tasks:
        t.cancel()
    mon.cancel(); probe.cancel(); hv.cancel()
    cpu = [s[1] for s in samples]; rss = [s[2] for s in samples]
    res = {
        "players": N, "profiles_s": round(t_prof, 1), "ramp_s": round(ramp, 1), "steady_s": round(dur), "connect_errors": errors["connect"], "dropped": errors["dropped"],
        "chat_ms": {"n": len(lat_chat), "p50": round(pct(lat_chat, 50)), "p95": round(pct(lat_chat, 95)), "p99": round(pct(lat_chat, 99)), "max": round(max(lat_chat or [0]))},
        "http_me_ms": {"n": len(lat_http), "p50": round(pct(lat_http, 50)), "p95": round(pct(lat_http, 95)), "max": round(max(lat_http or [0])), "errors": errors["http"]},
        "heavy_rest_ms": {"per_s": RATE, "n": len(lat_heavy), "p50": round(pct(lat_heavy, 50)), "p95": round(pct(lat_heavy, 95)), "max": round(max(lat_heavy or [0]))},
        "rx_msgs_per_s": round(msgs / dur), "rx_MB_per_s": round(byt / dur / 1e6, 2),
        "server_cpu_pct_avg": round(statistics.mean(cpu), 1) if cpu else None, "server_cpu_pct_max": round(max(cpu), 1) if cpu else None,
        "server_rss_MB_max": round(max(rss)) if rss else None,
    }
    print(json.dumps(res))

asyncio.run(main())
