"use strict";
// Sound engine: every sound is synthesized with WebAudio (no files, no copied assets).
// Master volume = localStorage "sfx" (0..1); 0 = off. Haptics go through Telegram's HapticFeedback when available.
const sfx = (() => {
  const lsGet = (k, d) => { try { return localStorage.getItem(k) ?? d; } catch { return d; } };
  let ctx, master, wet, noiseBuf, last = {};
  const vol = () => parseFloat(lsGet("sfx", "0.7")) || 0;

  function init() {
    if (ctx) return ctx;
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -14; comp.ratio.value = 6;
      master = ctx.createGain(); master.connect(comp); comp.connect(ctx.destination);
      // short synthetic room reverb: decaying noise impulse
      const len = ctx.sampleRate * .9, ir = ctx.createBuffer(2, len, ctx.sampleRate);
      for (let c = 0; c < 2; c++) { const d = ir.getChannelData(c); for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3); }
      const conv = ctx.createConvolver(); conv.buffer = ir; wet = ctx.createGain(); wet.gain.value = .22; wet.connect(conv); conv.connect(master);
      noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 1.5, ctx.sampleRate);
      const nd = noiseBuf.getChannelData(0); for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
    } catch { ctx = null; }
    return ctx;
  }
  const ready = () => { const v = vol(); if (!v || !init()) return false; if (ctx.state === "suspended") ctx.resume(); master.gain.value = v; return true; };
  const throttle = (k, ms) => { const n = performance.now(); if (n - (last[k] || 0) < ms) return true; last[k] = n; return false; };

  // oscillator note with attack/decay, optional pitch slide, lowpass and reverb send
  function tone(f, d = .15, o = {}) {
    const { type = "sine", v = 1, at = 0, a = .004, to = 0, lp = 0, rev = 0 } = o, s = ctx.currentTime + at;
    const os = ctx.createOscillator(), g = ctx.createGain(); os.type = type; os.frequency.setValueAtTime(f, s);
    if (to) os.frequency.exponentialRampToValueAtTime(to, s + d);
    g.gain.setValueAtTime(.0001, s); g.gain.exponentialRampToValueAtTime(.3 * v, s + a); g.gain.exponentialRampToValueAtTime(.0001, s + d);
    let n = os; if (lp) { const fl = ctx.createBiquadFilter(); fl.type = "lowpass"; fl.frequency.value = lp; os.connect(fl); n = fl; }
    n.connect(g); g.connect(master); if (rev) { const r = ctx.createGain(); r.gain.value = rev; g.connect(r); r.connect(wet); }
    os.start(s); os.stop(s + d + .05);
  }
  // filtered noise burst (whoosh, splat, fizz, thud body)
  function noise(d = .2, o = {}) {
    const { v = 1, at = 0, type = "bandpass", f0 = 1000, f1 = 0, q = 1, a = .01, rev = 0 } = o, s = ctx.currentTime + at;
    const src = ctx.createBufferSource(); src.buffer = noiseBuf; src.loop = true;
    const fl = ctx.createBiquadFilter(); fl.type = type; fl.Q.value = q; fl.frequency.setValueAtTime(f0, s);
    if (f1) fl.frequency.exponentialRampToValueAtTime(f1, s + d);
    const g = ctx.createGain(); g.gain.setValueAtTime(.0001, s); g.gain.exponentialRampToValueAtTime(.3 * v, s + a); g.gain.exponentialRampToValueAtTime(.0001, s + d);
    src.connect(fl); fl.connect(g); g.connect(master); if (rev) { const r = ctx.createGain(); r.gain.value = rev; g.connect(r); r.connect(wet); }
    src.start(s, Math.random()); src.stop(s + d + .05);
  }
  const arp = (notes, step, o = {}) => notes.forEach((f, i) => tone(f, o.d || .35, { type: o.type || "triangle", v: o.v || .8, at: i * step, rev: .5, a: .005 }));
  const haptic = (kind) => { try { const h = window.Telegram?.WebApp?.HapticFeedback; if (!h || !vol()) return; kind === "ok" || kind === "err" || kind === "warn" ? h.notificationOccurred(kind === "ok" ? "success" : kind === "err" ? "error" : "warning") : h.impactOccurred(kind); } catch { } };

  // cubic-bezier(.15,.55,.1,1) inverse: time at which the bottle has covered a given fraction of its rotation
  const bez = (t, a, b) => 3 * a * t * (1 - t) * (1 - t) + 3 * b * t * t * (1 - t) + t * t * t;
  const ease = x => { let lo = 0, hi = 1; for (let i = 0; i < 24; i++) { const m = (lo + hi) / 2; bez(m, .15, .1) < x ? lo = m : hi = m; } return bez((lo + hi) / 2, .55, 1); };

  const api = {
    unlock: () => { if (vol()) init() && ctx.state === "suspended" && ctx.resume(); },
    click: () => { if (!ready() || throttle("click", 40)) return; tone(760, .06, { type: "sine", to: 480, v: .6 }); },
    open: () => { if (!ready() || throttle("open", 120)) return; noise(.18, { f0: 500, f1: 2400, q: .8, v: .35 }); tone(520, .1, { to: 780, v: .3, type: "triangle" }); },
    close: () => { if (!ready() || throttle("close", 120)) return; noise(.14, { f0: 2000, f1: 500, q: .8, v: .25 }); },
    // bottle spin: air whoosh + wooden ratchet ticks that slow down exactly like the bottle (dur seconds, rotated deg)
    spin: (dur = 5, deg = 1800 + 180) => {
      if (!ready()) return; haptic("medium");
      noise(Math.min(dur, 2.2), { f0: 300, f1: 1800, q: .6, v: .3, a: .12 }); noise(dur, { f0: 1800, f1: 250, q: .5, v: .12, a: .5 });
      const per = 36, n = Math.floor(deg / per);   // one tick every 36 degrees
      for (let i = 1; i <= n; i++) {
        const frac = i * per / deg, tt = (() => { let lo = 0, hi = 1; for (let k = 0; k < 22; k++) { const m = (lo + hi) / 2; ease(m) < frac ? lo = m : hi = m; } return (lo + hi) / 2 * dur; })();
        const slow = tt / dur; tone(900 - slow * 380, .035, { type: "square", v: .13 + (1 - slow) * .07, at: tt, lp: 2600 });
        tone(190, .05, { type: "sine", v: .2, at: tt, to: 110 });
      }
      setTimeout(api.settle, dur * 820);
    },
    // measured on the original: one bright 1.8-2.7 kHz tick (~0.25 s) ~4.1 s into the spin
    settle: () => { if (!ready()) return; tone(1830, .1, { v: .9 }); tone(2153, .2, { at: .03, to: 1100, v: .7 }); noise(.07, { f0: 2800, q: 2, v: .5 }); tone(150, .16, { v: .35, to: 80 }); haptic("heavy"); },
    // measured: rising 1.6-2.3 kHz shimmer (~0.4 s) when the pair has met in the middle
    pair: () => { if (!ready()) return; arp([1637, 1830, 1981, 2196, 2261], .07, { d: .2, v: .55, type: "sine" }); noise(.2, { f0: 8000, type: "highpass", v: .18, at: .2, a: .05 }); haptic("light"); },
    // measured: two partials (861 + 1507 Hz) decaying over ~2.7 s; used as the "sound is on" confirmation
    bell: () => { if (!ready()) return; tone(861, 2.6, { v: .55, a: .004 }); tone(1507, 2.2, { v: .38, a: .004 }); tone(517, 1.4, { v: .15, a: .004 }); },
    kiss: () => {
      if (!ready()) return; haptic("ok");
      noise(.07, { f0: 2600, f1: 900, q: 2, v: .8 }); tone(1400, .09, { to: 520, v: .7, type: "sine" }); noise(.05, { f0: 3500, q: 3, v: .5, at: .09 });
      arp([784, 988, 1175, 1568], .08, { d: .5, v: .6 });
    },
    no: () => { if (!ready()) return; haptic("warn"); tone(330, .28, { type: "triangle", to: 250, v: .7, lp: 1800 }); tone(247, .42, { type: "triangle", to: 170, v: .7, at: .22, lp: 1500 }); },
    turn: () => { if (!ready() || throttle("turn", 800)) return; haptic("light"); arp([659, 880], .11, { d: .3, v: .8 }); },
    tick: () => { if (!ready() || throttle("tick", 300)) return; tone(1200, .04, { type: "square", v: .25, lp: 3000 }); },
    // gifts: category by emoji
    giftSend: e => { if (!ready()) return; noise(.5, { f0: 500, f1: 3200, q: .7, v: .35, a: .08 }); tone(500, .3, { to: 1100, v: .35, type: "triangle", at: .02 }); },
    giftHit: (e, at = 0) => {
      if (!ready()) return; const k = giftKind(e);
      if (k === "splat") { noise(.22, { f0: 700, f1: 160, q: .7, v: .9, at, type: "lowpass" }); tone(130, .18, { to: 60, v: .9, at }); }
      else if (k === "drink") { tone(2400, .25, { v: .45, at, rev: .6 }); tone(3100, .18, { v: .3, at: at + .03, rev: .6 }); noise(.5, { f0: 5000, type: "highpass", v: .2, at: at + .05, a: .1 }); }
      else if (k === "jewel") arp([1319, 1568, 2093, 2637], .06, { d: .45, v: .55 });
      else if (k === "royal") arp([523, 659, 784, 1046], .09, { d: .5, v: .8, type: "square" });
      else if (k === "flower") arp([659, 784, 988], .09, { d: .6, v: .6, type: "sine" });
      else if (k === "cute") { tone(900, .08, { to: 1400, v: .6, at }); tone(1400, .09, { to: 900, v: .6, at: at + .09 }); }
      else arp([740, 1110], .08, { d: .35, v: .7 });
    },
    giftGot: e => { if (!ready()) return; haptic("ok"); arp([880, 1318, 1760], .1, { d: .6, v: .9, type: "sine" }); api.giftHit(e, .3); },
    chat: () => { if (!ready() || throttle("chat", 250)) return; tone(880, .07, { v: .35, to: 1000 }); },
    pm: () => { if (!ready()) return; haptic("light"); arp([988, 1318], .1, { d: .35, v: .8 }); },
    heart: () => { if (!ready()) return; haptic("ok"); arp([1046, 1568], .07, { d: .35, v: .7, type: "sine" }); },
    coin: () => { if (!ready() || throttle("coin", 60)) return; tone(1976, .08, { type: "square", v: .3, lp: 4000 }); tone(2637, .22, { v: .5, at: .06, type: "triangle", rev: .4 }); },
    win: () => { if (!ready()) return; haptic("ok"); arp([523, 659, 784, 1046, 1318], .08, { d: .6, v: .9, type: "triangle" }); tone(262, .9, { v: .5, type: "sine", at: .35, rev: .5 }); },
    ach: () => { if (!ready()) return; haptic("ok"); arp([392, 523, 659, 784, 1046, 1318], .09, { d: .7, v: .9, type: "triangle" }); noise(.6, { f0: 6000, type: "highpass", v: .15, at: .4, a: .2 }); },
    // wheel of fortune: ticks as the pointer passes pegs, slowing with the spin, then result
    wheel: (dur = 5, deg = 1800) => {
      if (!ready()) return; haptic("medium"); const pegs = Math.floor(deg / 22.5);
      for (let i = 1; i <= pegs; i++) { const frac = i / pegs; let lo = 0, hi = 1; for (let k = 0; k < 22; k++) { const m = (lo + hi) / 2; ease(m) < frac ? lo = m : hi = m; } const tt = (lo + hi) / 2 * dur; tone(1500 - (tt / dur) * 700, .03, { type: "triangle", v: .3, at: tt }); }
    },
    wheelStop: win => { if (!ready()) return; win ? api.win() : tone(300, .35, { type: "triangle", to: 220, v: .6 }); },
    error: () => { if (!ready()) return; haptic("err"); tone(160, .18, { type: "sawtooth", v: .5, lp: 900 }); tone(130, .22, { type: "sawtooth", v: .5, at: .12, lp: 800 }); },
    join: () => { if (!ready() || throttle("join", 400)) return; tone(520, .1, { to: 700, v: .35, type: "triangle" }); },
    leave: () => { if (!ready() || throttle("leave", 400)) return; tone(520, .12, { to: 340, v: .3, type: "triangle" }); },
    gift: () => api.giftGot(""), // legacy name used by older call sites
  };
  function giftKind(e) {
    if (!e) return "";
    if ("🍅🐸🐷🍼🤡🍌".includes(e)) return "splat";
    if ("🍸🍹🍷🥃🥂🍾🍺🥛🍨🍰🥤".includes(e)) return "drink";
    if ("💎💍🏆🏅".includes(e)) return "jewel";
    if ("👑🔱🤴👸🎩🪖⚔️🦇".includes(e)) return "royal";
    if ("🌹🌷💐🥀🌿🌱🌵🍓💋".includes(e)) return "flower";
    if ("🦆🐧🍬🎲🧢🥚".includes(e)) return "cute";
    return "";
  }
  ["pointerdown", "touchstart", "keydown"].forEach(ev => document.addEventListener(ev, api.unlock, { once: true, passive: true }));
  return api;
})();
