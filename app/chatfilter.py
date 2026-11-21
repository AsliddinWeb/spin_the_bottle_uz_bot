"""Chat filter: bad words (uz/ru/en), links / @usernames / phone numbers, and repeated-message spam.

Words live in the `badwords` table so staff can change them from the bot (/addword, /delword) without a restart.
An entry ending with `*` is a stem (matches words that start with it), anything else must match a whole word.
Matching works on normalised text: lower-case, ё->е, apostrophes dropped, repeated letters collapsed
("suuuka" -> "suka"), single spaced-out letters re-joined ("с у к а" -> "сука").
It is a first line of defence, not a perfect censor: staff review (/filtered) and mutes cover the rest.
"""
import re
import time
from collections import deque

from . import db

SEED = """
блять бля блядь блядина хуй* хуе* хуя* хуи* нахуй пизд* ебат* ебан* ебал* ебла* ебуч* сука суки сучка сучара мудак* мудил*
гандон* долбоеб* долбаеб* залуп* пидор* пидар* пидр* шлюх* мразь ублюдок* уебок уебан
blyat blyad blya suka pidor* pidar* huy* xuy* hui nahuy naxuy ebat* ebal* ebanat* mudak* gandon* zalup*
sik sikay sikaman sikib sikish sikdim siktir* qotaq* qotoq* jalab* jalap* onangni ammangni skay skaman haromi*
fuck* shit shitty shithead shitface bitch* cunt* asshole* dickhead* nigger* nigga* faggot* whore* slut* retard* motherfuck*
""".split()

LINK_RE = re.compile(r"(https?://|www\.|t\.me/|telegram\.me/|\b[\w-]{2,}\.(com|ru|uz|org|net|me|io|xyz|info|ly|cc|tk|click|site|link)\b)", re.I)
HANDLE_RE = re.compile(r"(?<![\w])@[A-Za-z0-9_]{4,}")
PHONE_RE = re.compile(r"(?:\+?\d[\s\-().]{0,2}){7,}")
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
_stems: list[str] = []
_exact: set[str] = set()
_loaded = 0.0
_recent: dict[int, deque] = {}        # uid -> deque of (ts, normalised text)
_strikes: dict[int, deque] = {}       # uid -> deque of violation timestamps
FILTERED: deque = deque(maxlen=40)    # (ts, uid, kind, text) shown to staff by /filtered
STRIKE_LIMIT, STRIKE_WINDOW, STRIKE_MUTE = 3, 600, 600
REPEAT_N, REPEAT_WINDOW = 3, 25


def _squash(w: str) -> str:
    return re.sub(r"(.)\1+", r"\1", w)


def normalise(text: str) -> list[str]:
    t = text.lower().replace("ё", "е").replace("’", "").replace("'", "").replace("`", "").replace("ʻ", "")
    toks = WORD_RE.findall(t)
    out, buf = [], []
    for w in toks:               # re-join letters typed one by one: "с у к а"
        if len(w) == 1 and not w.isdigit():
            buf.append(w)
            continue
        if len(buf) >= 3:
            out.append("".join(buf))
        else:
            out.extend(buf)
        buf = []
        out.append(w)
    if len(buf) >= 3:
        out.append("".join(buf))
    else:
        out.extend(buf)
    return [_squash(w) for w in out]


def _init() -> None:
    db.x("CREATE TABLE IF NOT EXISTS badwords(word TEXT PRIMARY KEY, added_by INTEGER, ts INTEGER)")
    if not db.q1("SELECT 1 FROM badwords LIMIT 1"):
        for w in SEED:
            db.x("INSERT OR IGNORE INTO badwords VALUES(?,?,?)", w, 0, int(time.time()))
    reload()


def reload() -> None:
    global _loaded
    _stems.clear(); _exact.clear()
    for r in db.q("SELECT word FROM badwords"):
        w = r["word"]
        key = _squash(w.rstrip("*").lower().replace("ё", "е").replace("'", ""))
        if w.endswith("*"):
            _stems.append(key)
        else:
            _exact.add(key)
    _loaded = time.time()


def words() -> list[str]:
    return [r["word"] for r in db.q("SELECT word FROM badwords ORDER BY word")]


def add_word(word: str, by: int) -> bool:
    word = word.strip().lower()
    if not (2 <= len(word) <= 30) or " " in word:
        return False
    db.x("INSERT OR IGNORE INTO badwords VALUES(?,?,?)", word, by, int(time.time()))
    reload()
    return True


def del_word(word: str) -> bool:
    n = db.x("DELETE FROM badwords WHERE word=?", word.strip().lower()).rowcount
    reload()
    return n > 0


def bad_word(text: str) -> str | None:
    for w in normalise(text):
        if w in _exact or any(w.startswith(s) for s in _stems):
            return w
    return None


def check(uid: int, text: str, repeat: bool = True) -> str | None:
    """None when the text is fine, else 'words' | 'link' | 'phone' | 'repeat'. Also records strikes."""
    if not _loaded:
        _init()
    kind = None
    if bad_word(text):
        kind = "words"
    elif LINK_RE.search(text) or HANDLE_RE.search(text):
        kind = "link"
    elif PHONE_RE.search(text) and len(re.sub(r"\D", "", text)) >= 7:
        kind = "phone"
    elif repeat:
        now = time.time()
        key = " ".join(normalise(text))
        dq = _recent.setdefault(uid, deque(maxlen=6))
        while dq and now - dq[0][0] > REPEAT_WINDOW:
            dq.popleft()
        if sum(1 for _, k in dq if k == key) >= REPEAT_N - 1:
            kind = "repeat"
        dq.append((now, key))
    if kind:
        FILTERED.append((int(time.time()), uid, kind, text[:120]))
    return kind


def strike(uid: int) -> bool:
    """Count a violation; True when the player just reached the auto-mute limit."""
    now = time.time()
    dq = _strikes.setdefault(uid, deque())
    dq.append(now)
    while dq and now - dq[0] > STRIKE_WINDOW:
        dq.popleft()
    if len(dq) >= STRIKE_LIMIT:
        dq.clear()
        return True
    return False
