"""Real-time game engine: tables, turn loop, chat, gifts, music."""
import asyncio
import random
import re
import time
from collections import deque

import httpx

from . import chatfilter, config, db, moderation
from .catalog import (GESTURE_MAP, GESTURE_TTL, GIFT_MAP, GIFTS, HEAD_IDS, KISS_REWARD, TABLE_VIP_KISS_BONUS, dj_level)

SPIN_T = 20      # seconds the spinner has to press SPIN
DEC_T = 12       # seconds to answer the kiss prompt
SPIN_DUR = 5.0   # bottle animation
NEXT_GAP = 1.5   # pause between turns
GIFT_TTL = 86400  # seconds a gift stays on an avatar (it is stored, so it survives leaving / restarts)
LEFT = object()

YT_RE = re.compile(r"(?:youtu\.be/|v=|/embed/|/shorts/)([A-Za-z0-9_-]{11})")


def now_ms() -> int:
    return int(time.time() * 1000)


class Client:
    def __init__(self, ws, uid: int):
        self.ws = ws
        self.uid = uid
        self.table: "Table | None" = None
        self.last_chat = 0.0

    async def send(self, msg: dict) -> None:
        try:
            await self.ws.send_json(msg)
        except Exception:
            pass


class Player:
    def __init__(self, client: Client, seat: int, u):
        self.client = client
        self.uid = u["id"]
        self.seat = seat
        self.name = u["name"]
        self.age = u["age"]
        self.gender = u["gender"]
        self.photo = u["photo"]
        self.frame = u["frame"]
        self.bottle = u["bottle"]
        self.vip = db.is_vip(u)
        self.tkiss = 0
        self.gifts: dict[str, tuple[str, float]] = {}  # slot -> (emoji, ts), restored from the DB
        for r in db.q("SELECT slot, emoji, ts FROM worn WHERE user_id=? AND ts>?", u["id"], int(time.time()) - GIFT_TTL):
            self.gifts[r["slot"]] = (r["emoji"], float(r["ts"]))
        self.strikes = 0
        self.gesture: tuple[str, float] | None = None  # (emoji, ts)

    def public(self) -> dict:
        gifts = {slot: e for slot, (e, ts) in self.gifts.items() if time.time() - ts < GIFT_TTL}
        return {
            "seat": self.seat, "uid": self.uid, "name": self.name, "age": self.age,
            "gender": self.gender, "photo": self.photo, "frame": self.frame,
            "vip": self.vip, "kisses": self.tkiss, "gifts": gifts,
            "gesture": self.gesture[0] if self.gesture and time.time() - self.gesture[1] < GESTURE_TTL else "",
        }


class Table:
    def __init__(self, hub: "Hub", tid: int):
        self.hub = hub
        self.id = tid
        self.players: dict[int, Player] = {}  # uid -> Player
        self.phase = "waiting"
        self.turn_uid = 0
        self.target_uid = 0
        self.deadline = 0
        self.spin_id = 0
        self.spin_bottle = "bottle_green"
        self.result = ""
        self.chat: deque = deque(maxlen=60)
        self.chat_id = 0
        self.music: dict | None = None
        self.queue: list[dict] = []
        self.wake = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._fut: asyncio.Future | None = None
        self._expect: tuple | None = None
        self._last_turn = 0
        self._last_seat = -1
        self.kicks: dict[int, dict] = {}      # kicked uid -> {"by", "until", "task"}: pending kicks that can still be rescued
        self.kick_ban: dict[int, float] = {}  # uid -> time until which they cannot rejoin this table

    # ---- membership -------------------------------------------------
    def free_seat(self) -> int | None:
        used = {p.seat for p in self.players.values()}
        return next((i for i in range(config.MAX_SEATS) if i not in used), None)

    def counts(self) -> tuple[int, int]:
        m = sum(1 for p in self.players.values() if p.gender == "m")
        f = sum(1 for p in self.players.values() if p.gender == "f")
        return m, f

    async def join(self, client: Client) -> bool:
        seat = self.free_seat()
        if seat is None:
            return False
        u = db.get_user(client.uid)
        self.players[client.uid] = Player(client, seat, u)
        client.table = self
        db.touch_recent(client.uid, self.id)
        if len(self.players) >= 2:
            self.wake.set()
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self.run())
        await client.send({"t": "joined", "table": self.id, "history": list(self.chat)})
        await self.broadcast()
        return True

    def kick_banned(self, uid: int) -> bool:
        return self.kick_ban.get(uid, 0) > time.time()

    async def leave(self, uid: int) -> None:
        p = self.players.pop(uid, None)
        if not p:
            return
        k = self.kicks.pop(uid, None)
        if k:   # leaving while kicked counts as being kicked (no dodging the ban)
            k["task"].cancel()
            self.kick_ban[uid] = time.time() + config.KICK_BAN_MIN * 60
        if not self.players:
            for kk in self.kicks.values():
                kk["task"].cancel()
            self.kicks.clear()
        if p.client.table is self:
            p.client.table = None
        if self._fut and not self._fut.done() and uid in (self.turn_uid, self.target_uid):
            self._fut.set_result(LEFT)
        if self.music and self.music.get("by_uid") == uid and not self.players:
            self.music, self.queue = None, []
        await self.broadcast()

    # ---- state ------------------------------------------------------
    def state(self) -> dict:
        return {
            "t": "state", "id": self.id, "phase": self.phase, "turn": self.turn_uid,
            "target": self.target_uid, "deadline": self.deadline, "now": now_ms(),
            "spin": {"id": self.spin_id, "dur": SPIN_DUR, "bottle": self.spin_bottle},
            "result": self.result,
            "seats": [p.public() for p in sorted(self.players.values(), key=lambda p: p.seat)],
            "music": self.music and {k: v for k, v in self.music.items() if k != "by_uid"},
            "queue": len(self.queue),
            "kicks": [{"uid": u, "by": k["by"], "left": max(0, int(k["until"] - time.time() + .999))} for u, k in self.kicks.items()],
        }

    async def broadcast(self, msg: dict | None = None) -> None:
        msg = msg or self.state()
        await asyncio.gather(*(p.client.send(msg) for p in list(self.players.values())))

    async def say(self, kind: str, **kw) -> None:
        self.chat_id += 1
        m = {"t": "chat", "id": self.chat_id, "k": kind, "ts": int(time.time()), **kw}
        self.chat.append(m)
        await self.broadcast(m)

    def set_deadline(self, sec: float) -> None:
        self.deadline = now_ms() + int(sec * 1000)

    # ---- turn loop ----------------------------------------------------
    async def wait(self, uid: int, kind: str, timeout: float):
        loop = asyncio.get_running_loop()
        self._fut, self._expect = loop.create_future(), (uid, kind)
        try:
            return await asyncio.wait_for(self._fut, timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._fut, self._expect = None, None

    def deliver(self, uid: int, kind: str, value=True) -> None:
        if self._fut and not self._fut.done() and self._expect == (uid, kind):
            self._fut.set_result(value)

    def pick_target(self, spinner: Player) -> Player | None:
        others = [p for p in self.players.values() if p.uid != spinner.uid]
        if not others:
            return None
        weights = []
        for p in others:
            w = 1.0
            if spinner.gender and p.gender and spinner.gender != p.gender:
                w *= 3
            inv = db.q1("SELECT armed FROM inventory WHERE user_id=? AND item='magnet'", p.uid)
            if inv and inv["armed"] > 0:
                w *= 4
            weights.append(w)
        target = random.choices(others, weights)[0]
        db.consume_armed(target.uid, "magnet")
        return target

    async def run(self) -> None:
        try:
            while self.players:
                if len(self.players) < 2:
                    self.phase, self.turn_uid, self.target_uid, self.deadline, self.result = "waiting", 0, 0, 0, ""
                    self.wake.clear()  # clear before any await so a join during broadcast isn't lost
                    await self.broadcast()
                    if len(self.players) < 2:
                        await self.wake.wait()
                    continue
                await self.one_turn()
                if len(self.players) >= 2:   # short "waiting for the next turn" gap between turns (as in the original)
                    self.phase, self.turn_uid, self.target_uid, self.deadline, self.result = "between", 0, 0, 0, ""
                    await self.broadcast()
                    await asyncio.sleep(NEXT_GAP)
        except asyncio.CancelledError:
            raise
        except Exception:
            import traceback
            traceback.print_exc()
            await asyncio.sleep(2)
            if self.players:
                self._task = asyncio.create_task(self.run())

    async def one_turn(self) -> None:
        order = sorted(self.players.values(), key=lambda p: p.seat)
        last = self.players.get(self._last_turn)
        last_seat = last.seat if last else self._last_seat
        spinner = next((p for p in order if p.seat > last_seat), order[0])
        self._last_turn, self._last_seat = spinner.uid, spinner.seat
        self.turn_uid, self.target_uid, self.result = spinner.uid, 0, ""

        self.phase = "spin_wait"
        self.set_deadline(SPIN_T)
        await self.broadcast()
        act = await self.wait(spinner.uid, "spin", SPIN_T)
        if act is LEFT or spinner.uid not in self.players:
            return
        if act is None:
            spinner.strikes += 1
            if spinner.strikes >= 3:
                await self.kick(spinner.uid, "afk")
            return
        spinner.strikes = 0

        target = self.pick_target(spinner)
        if not target:
            return
        db.inc(spinner.uid, "spins")
        await self.notify_achievements(spinner.uid)
        self.target_uid = target.uid
        self.spin_id += 1
        self.spin_bottle = spinner.bottle
        self.phase = "spinning"
        self.set_deadline(SPIN_DUR)
        await self.broadcast()
        await asyncio.sleep(SPIN_DUR + 0.4)
        if spinner.uid not in self.players or target.uid not in self.players:
            return

        self.phase = "ask_spinner"
        self.set_deadline(DEC_T)
        await self.broadcast()
        ans = await self.wait(spinner.uid, "decide", DEC_T)
        if ans is LEFT or spinner.uid not in self.players or target.uid not in self.players:
            return
        if ans is not True:
            await self.finish("no")
            return

        self.phase = "ask_target"
        self.set_deadline(DEC_T)
        await self.broadcast()
        ans = await self.wait(target.uid, "decide", DEC_T)
        if ans is LEFT or spinner.uid not in self.players or target.uid not in self.players:
            return
        if ans is not True:
            await self.finish("no")
            return

        await self.kiss(spinner, target)

    async def finish(self, result: str, pause: float = 2.4) -> None:
        self.phase, self.result = "result", result
        self.set_deadline(0)
        await self.broadcast()
        await asyncio.sleep(pause)

    async def kiss(self, a: Player, b: Player) -> None:
        counted = db.pair_kiss(a.uid, b.uid) <= config.PAIR_DAILY_CAP   # beyond the cap the kiss still pays, but stays out of the day/week/month lists
        for p in (a, b):
            reward = KISS_REWARD + (TABLE_VIP_KISS_BONUS if p.vip else 0)
            if db.consume_armed(p.uid, "double"):
                reward *= 2
            db.add_hearts(p.uid, reward)
            db.inc(p.uid, "kisses", daily=counted)
            p.tkiss += 1
        await self.say("kiss", uid=a.uid, name=a.name, to_uid=b.uid, to_name=b.name)
        for p in (a, b):
            await self.notify_achievements(p.uid)
        await self.finish("kiss", 3.6)

    async def notify_achievements(self, uid: int) -> None:
        new = db.check_achievements(uid)
        c = self.hub.clients.get(uid)
        if c:
            for aid in new:
                await c.send({"t": "ach", "id": aid})
            await self.hub.push_me(uid)

    async def kick(self, uid: int, reason: str) -> None:
        p = self.players.get(uid)
        if not p:
            return
        c = p.client
        await self.leave(uid)
        await c.send({"t": "left", "reason": reason})

    # ---- kick & rescue ------------------------------------------------
    async def handle_kick(self, client: Client, to_uid: int) -> None:
        me, tgt = self.players.get(client.uid), self.players.get(to_uid)
        if not me or not tgt or to_uid == client.uid:
            return
        toast = lambda key: client.send({"t": "toast", "key": key})
        if len(self.players) < config.KICK_MIN_PLAYERS:
            return await toast("kick_few")
        if moderation.rank(to_uid) > 0:
            return await toast("kick_staff")
        if to_uid in self.kicks:
            return await toast("kick_pending")
        if any(k["by"] == client.uid for k in self.kicks.values()):
            return await toast("kick_busy")
        if moderation.active(client.uid, "mute"):
            return await toast("muted")
        now = int(time.time())
        # the free kick is claimed atomically; otherwise it costs hearts
        free = db.x("UPDATE users SET kick_free_ts=? WHERE id=? AND kick_free_ts<=?", now + config.KICK_FREE_EVERY, client.uid, now).rowcount == 1
        if not free and not db.spend_hearts(client.uid, config.KICK_PRICE):
            return await toast("no_hearts")
        self.kicks[to_uid] = {"by": client.uid, "until": time.time() + config.KICK_DELAY, "task": asyncio.create_task(self._kick_timer(to_uid))}
        moderation.audit(client.uid, "player_kick", to_uid, f"table {self.id}" + ("" if free else f" paid {config.KICK_PRICE}"))
        await self.say("kick", uid=client.uid, name=me.name, to_uid=to_uid, to_name=tgt.name, secs=config.KICK_DELAY)
        await self.broadcast()
        await self.hub.push_me(client.uid)

    async def handle_rescue(self, client: Client, to_uid: int) -> None:
        me, tgt, k = self.players.get(client.uid), self.players.get(to_uid), self.kicks.get(to_uid)
        if not me or not tgt or not k or to_uid == client.uid or k["by"] == client.uid:
            return
        if not db.spend_hearts(client.uid, config.RESCUE_PRICE):
            return await client.send({"t": "toast", "key": "no_hearts"})
        k = self.kicks.pop(to_uid, None)
        if not k:   # the timer fired while we were paying: give the hearts back
            db.add_hearts(client.uid, config.RESCUE_PRICE)
            return
        k["task"].cancel()
        moderation.audit(client.uid, "player_rescue", to_uid, f"table {self.id}")
        await self.say("rescue", uid=client.uid, name=me.name, to_uid=to_uid, to_name=tgt.name)
        await self.broadcast()
        await self.hub.push_me(client.uid)

    async def _kick_timer(self, uid: int) -> None:
        try:
            await asyncio.sleep(config.KICK_DELAY)
        except asyncio.CancelledError:
            return
        k, p = self.kicks.pop(uid, None), self.players.get(uid)
        if not k or not p:
            return
        if len(self.players) < config.KICK_MIN_PLAYERS:   # the table emptied meanwhile: the kick is void
            await self.broadcast()
            return
        self.kick_ban[uid] = time.time() + config.KICK_BAN_MIN * 60
        await self.say("kickout", uid=uid, name=p.name)
        await self.kick(uid, "kicked")

    # ---- chat / gifts / music ----------------------------------------
    async def handle_chat(self, client: Client, text: str) -> None:
        p = self.players.get(client.uid)
        text = (text or "").strip()[:200]
        if not p or not text or time.time() - client.last_chat < 0.7:
            return
        if moderation.active(client.uid, "mute"):
            await client.send({"t": "toast", "key": "muted"})
            return
        if kind := chatfilter.check(client.uid, text):  # blocked: not delivered, the sender is told why
            await client.send({"t": "toast", "key": "filtered_" + kind})
            if chatfilter.strike(client.uid) and moderation.rank(client.uid) == 0:
                moderation.sanction(0, client.uid, "mute", chatfilter.STRIKE_MUTE, "auto: chat filter")
                await client.send({"t": "toast", "key": "muted"})
                from . import botadmin
                await botadmin.notify_player(client.uid, "mute", "auto: chat filter", int(time.time()) + chatfilter.STRIKE_MUTE)
            return
        client.last_chat = time.time()
        db.inc(p.uid, "msgs")
        await self.say("msg", uid=p.uid, name=p.name, photo=p.photo, vip=p.vip, text=text)
        await self.notify_achievements(p.uid)

    async def handle_gift(self, client: Client, to_uid: int, gift_id: str, url: str = "") -> None:
        sender = self.players.get(client.uid)
        target = self.players.get(to_uid)
        g = GIFT_MAP.get(gift_id)
        if not sender or not g:
            return
        is_music = g[3] in ("music_now", "music_queue")  # music is for the whole table: no target needed
        if not is_music and (not target or to_uid == client.uid):
            return
        _, emoji, price, kind, vip_only = g
        u = db.get_user(client.uid)
        if vip_only and not db.is_vip(u):
            await client.send({"t": "toast", "key": "need_vip"})
            return
        vid = ""
        if kind in ("music_now", "music_queue"):
            m = YT_RE.search(url or "")
            if not m:
                await client.send({"t": "toast", "key": "bad_url"})
                return
            vid = m.group(1)
        if not db.spend_hearts(client.uid, price):
            await client.send({"t": "toast", "key": "no_hearts"})
            return

        if kind == "random":
            pool = [x for x in GIFTS if x[3] == "gift" and not x[4] and x[2] <= 3]
            gift_id, emoji, _, kind, _ = random.choice(pool)

        db.inc(client.uid, "gifts_sent")
        blocked = False
        if not is_music:
            db.inc(to_uid, "gifts_received")
            blocked = kind == "bad" and db.consume_armed(to_uid, "shield")
        if not blocked and not is_music:  # keep a permanent record: shows up in the receiver's profile
            db.x("INSERT INTO gifts_log(sender,target,gift,emoji,ts) VALUES(?,?,?,?,?)",
                 client.uid, to_uid, gift_id, emoji, int(time.time()))

        level_up = 0
        if vid:
            before = db.get_user(client.uid)["tracks"]
            db.inc(client.uid, "tracks")
            if dj_level(before + 1) > dj_level(before):
                level_up = dj_level(before + 1)
            title = await fetch_title(vid)
            db.x("INSERT INTO tracks_log(user_id,vid,title,ts) VALUES(?,?,?,?)", client.uid, vid, title, int(time.time()))
            track = {"vid": vid, "title": title, "by": sender.name, "by_uid": sender.uid,
                     "tid": f"{vid}-{now_ms()}"}
            if g[3] == "music_now" or not self.music:
                self.music = track
            else:
                self.queue.append(track)
            await self.say("music", uid=sender.uid, name=sender.name, title=title, now=g[3] == "music_now")
            if level_up:
                await self.say("dj", uid=sender.uid, name=sender.name, photo=sender.photo, level=level_up)
        else:
            if not blocked:
                slot = "head" if gift_id in HEAD_IDS else "hand"
                target.gifts[slot] = (emoji, time.time())
                db.x("INSERT OR REPLACE INTO worn VALUES(?,?,?,?)", to_uid, slot, emoji, int(time.time()))
            await self.say("gift", uid=sender.uid, name=sender.name, to_uid=target.uid,
                           to_name=target.name, gift=emoji, blocked=bool(blocked))
        await self.broadcast()
        for uid in ((client.uid,) if is_music else (client.uid, to_uid)):
            await self.notify_achievements(uid)

    async def handle_gesture(self, client: Client, gid: str) -> None:
        p, g = self.players.get(client.uid), GESTURE_MAP.get(gid)
        if not p or not g:
            return
        _, emoji, price, stat, need, vip_only = g
        u = db.get_user(client.uid)
        if (vip_only and not db.is_vip(u)) or (stat and u[stat] < need):
            await client.send({"t": "toast", "key": "need_vip" if vip_only else "gesture_locked"})
            return
        cur = db.x("UPDATE users SET smiles=smiles-? WHERE id=? AND smiles>=?", price, client.uid, price)
        if cur.rowcount != 1:
            await client.send({"t": "toast", "key": "no_smiles"})
            return
        p.gesture = (emoji, time.time())
        await self.broadcast()
        await self.hub.push_me(client.uid)

    async def music_ended(self, tid: str) -> None:
        if self.music and self.music["tid"] == tid:
            self.music = self.queue.pop(0) if self.queue else None
            await self.broadcast()


async def fetch_title(vid: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get("https://www.youtube.com/oembed",
                            params={"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"})
            if r.status_code == 200:
                return r.json().get("title", vid)[:80]
    except Exception:
        pass
    return vid


class Hub:
    def __init__(self):
        self.clients: dict[int, Client] = {}
        self.tables: dict[int, Table] = {}

    def table(self, tid: int) -> Table | None:
        if not 1 <= tid <= config.TABLE_COUNT:
            return None
        if tid not in self.tables:
            self.tables[tid] = Table(self, tid)
        return self.tables[tid]

    def pick_random(self, exclude: int = 0) -> Table:
        ts = [self.table(i) for i in range(1, config.TABLE_COUNT + 1)]
        ts = [t for t in ts if t.id != exclude and len(t.players) < config.MAX_SEATS]
        pool = [t for t in ts if len(t.players) >= 2] or [t for t in ts if len(t.players) == 1]
        if pool:
            return random.choices(pool, [len(t.players) for t in pool])[0]
        return next(t for t in ts if not t.players)

    async def connect(self, ws, uid: int) -> Client:
        old = self.clients.get(uid)
        if old:
            await self.drop(old)
            try:
                await old.ws.close(4001)
            except Exception:
                pass
        c = Client(ws, uid)
        self.clients[uid] = c
        return c

    async def drop(self, c: Client) -> None:
        if c.table:
            await c.table.leave(c.uid)
        if self.clients.get(c.uid) is c:
            del self.clients[c.uid]

    async def private_message(self, c: Client, to: int, text: str) -> None:
        text = text.strip()[:300]
        target = self.clients.get(to)
        if not text or to == c.uid or time.time() - c.last_chat < 0.7:
            return
        c.last_chat = time.time()
        u = db.get_user(c.uid)
        if not target:
            await c.send({"t": "toast", "key": "pm_offline"})
            return
        await target.send({"t": "pm", "uid": c.uid, "name": u["name"], "photo": u["photo"], "text": text})
        await c.send({"t": "toast", "key": "pm_sent"})

    async def push_court(self, target_uid: int) -> None:
        """Tell a (connected) target that someone started courting them."""
        c = self.clients.get(target_uid)
        row = db.q1("SELECT c.*, u.name, u.photo FROM courtship c JOIN users u ON u.id=c.suitor WHERE c.target=? AND c.seen=0", target_uid)
        if c and row:
            await c.send({"t": "court", "uid": row["suitor"], "name": row["name"], "photo": row["photo"], "price": row["price"]})
            db.x("UPDATE courtship SET seen=1 WHERE target=?", target_uid)

    async def apply_sanctions(self, uid: int) -> None:
        """Called right after a ban/kick so a connected player is removed immediately."""
        c = self.clients.get(uid)
        if not c:
            return
        from . import auth
        info = auth.ban_info(uid)
        if info:
            await c.send({"t": "banned", **info})
            await self.drop(c)
            try:
                await c.ws.close(4004)
            except Exception:
                pass

    async def kick_player(self, uid: int, reason: str = "kicked") -> bool:
        c = self.clients.get(uid)
        if c and c.table:
            await c.table.kick(uid, reason)
            return True
        return False

    async def push_me(self, uid: int) -> None:
        from .economy import me_payload
        c = self.clients.get(uid)
        if c:
            await c.send({"t": "me", "me": me_payload(uid)})

    async def dispatch(self, c: Client, m: dict) -> None:
        t = m.get("t")
        if t == "join":
            tid = m.get("table")
            cur = c.table.id if c.table else 0
            if tid in (None, "random", 0):
                table = self.pick_random(exclude=cur)
            else:
                table = self.table(int(tid))
            if not table:
                return
            if table.kick_banned(c.uid):   # kicked from that table recently
                await c.send({"t": "toast", "key": "kick_banned"})
                if tid not in (None, "random", 0):
                    return
                table = next((x for x in (self.pick_random(exclude=cur) for _ in range(8)) if not x.kick_banned(c.uid)), None)
                if not table:
                    return
            if cur == table.id:
                await c.send({"t": "joined", "table": table.id, "history": list(table.chat)})
                await table.broadcast()
                return
            if c.table:
                await c.table.leave(c.uid)
            if not await table.join(c):
                await c.send({"t": "toast", "key": "table_full"})
                await self.dispatch(c, {"t": "join", "table": "random"})
        elif t == "pm":
            await self.private_message(c, int(m.get("to", 0)), str(m.get("text", "")))
        elif t == "leave" and c.table:
            await c.table.leave(c.uid)
            await c.send({"t": "left", "reason": "leave"})
        elif c.table:
            tb = c.table
            if t == "spin":
                tb.deliver(c.uid, "spin")
            elif t == "decide":
                tb.deliver(c.uid, "decide", bool(m.get("v")))
            elif t == "chat":
                await tb.handle_chat(c, m.get("text", ""))
            elif t == "gift":
                await tb.handle_gift(c, int(m.get("to", 0)), str(m.get("gift", "")), str(m.get("url", "")))
            elif t == "kick":
                await tb.handle_kick(c, int(m.get("to", 0)))
            elif t == "rescue":
                await tb.handle_rescue(c, int(m.get("to", 0)))
            elif t == "gesture":
                await tb.handle_gesture(c, str(m.get("id", "")))
            elif t == "music_ended":
                await tb.music_ended(str(m.get("tid", "")))


hub = Hub()
