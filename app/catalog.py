"""Static game content: gifts, shop packs, items, achievements, wheel."""

# (id, emoji, price in hearts, kind, vip_only)
GIFTS = [
    ("music_now", "📼", 9, "music_now", False),
    ("music_queue", "🎧", 5, "music_queue", False),
    ("crown1", "👑", 3, "gift", False),
    ("crown2", "🔱", 3, "gift", False),
    ("king", "🤴", 3, "gift", False),
    ("queen", "👸", 3, "gift", False),
    ("medal", "🏅", 3, "gift", False),
    ("propeller", "🧢", 2, "gift", False),
    ("egg", "🥚", 1, "gift", False),
    ("smoothie", "🥤", 2, "gift", False),
    ("leaf", "🍁", 1, "gift", False),
    ("wreath", "🌼", 2, "gift", False),
    ("basket", "🧺", 1, "gift", False),
    ("lips", "💋", 1, "gift", False),
    ("gem", "💎", 1, "gift", False),
    ("strawberry", "🍓", 1, "gift", False),
    ("tomato", "🍅", 1, "bad", False),
    ("frog", "🐸", 2, "bad", False),
    ("rose", "🌹", 1, "gift", False),
    ("candy", "🍬", 1, "gift", False),
    ("duck", "🦆", 1, "gift", False),
    ("pig", "🐷", 1, "gift", False),
    ("penguin", "🐧", 1, "gift", False),
    ("tulip", "🌷", 1, "gift", False),
    ("bouquet", "💐", 1, "gift", False),
    ("plant", "🪴", 1, "gift", False),
    ("cactus", "🌵", 1, "gift", False),
    ("icecream", "🍦", 1, "gift", False),
    ("cake", "🍰", 1, "gift", False),
    ("milk", "🥛", 1, "gift", False),
    ("tea", "🍵", 1, "gift", False),
    ("cola", "🥫", 1, "gift", False),
    ("wine", "🍷", 1, "gift", False),
    ("whisky", "🥃", 1, "gift", False),
    ("blackrose", "🥀", 1, "gift", False),
    ("batcrown", "🦇", 3, "gift", False),
    ("ring", "💍", 1, "gift", False),
    ("dice", "🎲", 1, "random", False),
    ("joker", "🤡", 2, "bad", False),
    ("cocktail", "🍹", 2, "gift", True),
    ("martini", "🍸", 2, "gift", True),
    ("champagne", "🥂", 2, "gift", True),
    ("sombrero", "🤠", 2, "gift", True),
    ("viking", "🪖", 3, "gift", True),
    ("pirate", "🏴‍☠️", 3, "gift", True),
    ("tophat", "🎩", 3, "gift", True),
    ("diamondring", "💠", 4, "gift", True),
    ("trophy", "🏆", 5, "gift", True),
]
GIFT_MAP = {g[0]: g for g in GIFTS}
# gifts worn on the head; everything else sits in the avatar's corner ("hand")
HEAD_IDS = {"crown1", "crown2", "propeller", "king", "queen", "batcrown", "joker", "viking", "pirate", "tophat", "sombrero", "wreath"}

# Telegram Stars packs: id -> (stars, hearts, bonus%)
PACKS = {
    "p50": (50, 50, 0),
    "p250": (250, 250, 0),
    "p500": (500, 500, 0),
    "p1000": (1000, 1200, 20),
    "p2500": (2500, 3125, 25),
    "p5000": (5000, 7000, 40),
}
VIP_STARS = 300
VIP_DAYS = 30

# Shop items bought with hearts. kind: frame | bottle | booster
ITEMS = {
    "frame_gold": {"kind": "frame", "price": 30, "emoji": "🖼️"},
    "frame_neon": {"kind": "frame", "price": 40, "emoji": "🖼️"},
    "frame_hearts": {"kind": "frame", "price": 50, "emoji": "🖼️"},
    "frame_ice": {"kind": "frame", "price": 60, "emoji": "🖼️"},
    "frame_fire": {"kind": "frame", "price": 80, "emoji": "🖼️"},
    "frame_rose": {"kind": "frame", "price": 40, "emoji": "🖼️"},
    "frame_candy": {"kind": "frame", "price": 40, "emoji": "🖼️"},
    "frame_emerald": {"kind": "frame", "price": 50, "emoji": "🖼️"},
    "frame_royal": {"kind": "frame", "price": 60, "emoji": "🖼️"},
    "frame_casino": {"kind": "frame", "price": 60, "emoji": "🖼️"},
    "frame_night": {"kind": "frame", "price": 50, "emoji": "🖼️"},
    "frame_wood": {"kind": "frame", "price": 30, "emoji": "🖼️"},
    "frame_jungle": {"kind": "frame", "price": 60, "emoji": "🖼️"},
    "frame_castle": {"kind": "frame", "price": 70, "emoji": "🖼️"},
    "frame_chain": {"kind": "frame", "price": 70, "emoji": "🖼️"},
    "frame_cards": {"kind": "frame", "price": 60, "emoji": "🖼️"},
    "frame_diamond": {"kind": "frame", "price": 100, "emoji": "🖼️"},
    "frame_tech": {"kind": "frame", "price": 80, "emoji": "🖼️"},
    "frame_thorns": {"kind": "frame", "price": 80, "emoji": "🖼️"},
    "frame_cane": {"kind": "frame", "price": 60, "emoji": "🖼️"},
    "frame_filigree": {"kind": "frame", "price": 100, "emoji": "🖼️"},
    "frame_galaxy": {"kind": "frame", "price": 90, "emoji": "🖼️"},
    "frame_sakura": {"kind": "frame", "price": 70, "emoji": "🖼️"},
    "frame_inferno": {"kind": "frame", "price": 120, "emoji": "🖼️"},
    "bottle_green": {"kind": "bottle", "price": 0, "emoji": "🍾"},
    "bottle_brown": {"kind": "bottle", "price": 5, "emoji": "🍾"},
    "bottle_amber": {"kind": "bottle", "price": 5, "emoji": "🍾"},
    "bottle_red": {"kind": "bottle", "price": 5, "emoji": "🍾"},
    "bottle_blue": {"kind": "bottle", "price": 5, "emoji": "🍾"},
    "bottle_clear": {"kind": "bottle", "price": 5, "emoji": "🍾"},
    "bottle_milk": {"kind": "bottle", "price": 5, "emoji": "🍾"},
    "bottle_wine": {"kind": "bottle", "price": 5, "emoji": "🍾"},
    "bottle_champagne": {"kind": "bottle", "price": 5, "emoji": "🍾"},
    "bottle_cola": {"kind": "bottle", "price": 5, "emoji": "🍾"},
    "bottle_gold": {"kind": "bottle", "price": 10, "emoji": "🍾"},
    "bottle_rainbow": {"kind": "bottle", "price": 15, "emoji": "🍾"},
    "magnet": {"kind": "booster", "price": 20, "emoji": "🧲"},
    "double": {"kind": "booster", "price": 15, "emoji": "✨"},
    "shield": {"kind": "booster", "price": 10, "emoji": "🛡️"},
}
DEFAULT_BOTTLE = "bottle_green"

# wheel chances sold in packs: amount -> price in hearts (same packs as the original shop)
CHANCE_PACKS = {1: 5, 5: 20, 15: 45, 50: 150, 300: 900}
CHANCE_PRICE = CHANCE_PACKS[1]  # hearts for a single chance

# Achievements are generated per stat: (id, stat, threshold, reward hearts). Ids look like "kisses_50".
_TIERS = {
    "kisses": [1, 5, 10, 25, 50, 100, 200, 300, 500, 750, 1000, 1500, 2000, 3000, 5000, 7500, 10000],
    "spins": [1, 10, 25, 50, 100, 200, 300, 500, 750, 1000, 1500, 2000, 3000, 5000],
    "gifts_sent": [1, 5, 10, 25, 50, 100, 200, 300, 500, 750, 1000, 1500, 2500, 5000],
    "gifts_received": [1, 5, 10, 20, 50, 100, 200, 300, 500, 750, 1000, 1500, 2500, 5000],
    "msgs": [1, 10, 50, 100, 250, 500, 1000, 2000, 3000, 5000, 10000],
    "streak": [2, 3, 5, 7, 10, 14, 21, 30, 50, 100],
    "tracks": [1, 5, 10, 25, 50, 100, 250, 500, 1000],
}
ACHIEVEMENTS = [(f"{stat}_{n}", stat, n, 5 + int(n ** 0.6)) for stat, ns in _TIERS.items() for n in ns]
# ids used before the generator existed -> new ids (migrated in db.py)
OLD_ACH_IDS = {"first_kiss": "kisses_1", "kisses10": "kisses_10", "kisses50": "kisses_50", "kisses200": "kisses_200",
               "spins10": "spins_10", "spins100": "spins_100", "gifts5": "gifts_sent_5", "gifts50": "gifts_sent_50",
               "popular": "gifts_received_20", "chatter": "msgs_50", "streak5": "streak_5"}

DAILY = [1, 2, 3, 4, 5]

# Wheel of luck: 16 segments (kind, amount, weight)
WHEEL = [
    ("hearts", 3, 10), ("chance", 1, 6), ("smiles", 5, 7), ("hearts", 25, 2),
    ("chance", 3, 2), ("hearts", 1, 14), ("hearts", 100, 0.8), ("smiles", 3, 10),
    ("hearts", 10, 4), ("hearts", 5, 7), ("smiles", 10, 3), ("hearts", 1, 14),
    ("hearts", 3, 10), ("chance", 1, 6), ("hearts", 1000, 0.05), ("hearts", 25, 2),
]

# DJ level = number of thresholds reached by the tracks a player has put on
DJ_LEVELS = [1, 5, 15, 40, 100, 250]


def dj_level(tracks: int) -> int:
    return sum(1 for n in DJ_LEVELS if tracks >= n)


# Gestures: (id, emoji, price in smiles, unlock stat, needed, vip_only). They replace your avatar for a short time.
GESTURES = [
    ("nohearts", "🥺", 1, "", 0, False), ("skull", "💀", 3, "", 0, False),
    ("laugh", "🤣", 1, "", 0, True), ("cool", "😎", 1, "", 0, True), ("party", "🥳", 1, "", 0, True),
    ("wink", "😉", 1, "kisses", 1, False), ("kiss", "😘", 1, "kisses", 10, False), ("love", "😍", 1, "kisses", 50, False),
    ("sad", "😢", 1, "spins", 10, False), ("angry", "😡", 1, "spins", 100, False),
    ("shy", "🙈", 1, "gifts_sent", 5, False), ("star", "🤩", 1, "gifts_sent", 50, False),
    ("think", "🤔", 1, "msgs", 50, False), ("sleep", "😴", 1, "streak", 5, False), ("devil", "😈", 2, "gifts_received", 20, False),
]
GESTURE_MAP = {g[0]: g for g in GESTURES}
GESTURE_TTL = 120   # seconds a gesture stays on the avatar
VIP_SMILES = 5      # smiles a VIP can collect every day
START_SMILES = 3

# "Compliments" task: rate other players with one of these tags; 10 ratings pay hearts once
TAGS = ["argues", "hair", "flatterer", "fun", "drinks", "greedy"]
TAG_TASK_NEED = 10
TAG_TASK_REWARD = 10

TABLE_VIP_KISS_BONUS = 1
KISS_REWARD = 1
