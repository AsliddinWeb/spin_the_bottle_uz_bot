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
  const arp = (notes, step, o = {}) => notes.forEach((f, i) => tone(f, o.d || .35, { type: o.type || "triangle", v: o.v || .8, at: (o.at || 0) + i * step, rev: .5, a: .005 }));
  const haptic = (kind) => { try { const h = window.Telegram?.WebApp?.HapticFeedback; if (!h || !vol()) return; kind === "ok" || kind === "err" || kind === "warn" ? h.notificationOccurred(kind === "ok" ? "success" : kind === "err" ? "error" : "warning") : h.impactOccurred(kind); } catch { } };

  // cubic-bezier(.15,.55,.1,1) inverse: time at which the bottle has covered a given fraction of its rotation
  const bez = (t, a, b) => 3 * a * t * (1 - t) * (1 - t) + 3 * b * t * t * (1 - t) + t * t * t;
  const ease = x => { let lo = 0, hi = 1; for (let i = 0; i < 24; i++) { const m = (lo + hi) / 2; bez(m, .15, .1) < x ? lo = m : hi = m; } return bez((lo + hi) / 2, .55, 1); };


  // ---- every gift has its own sound (all synthesized). `at` delays it (seconds).
  const glug = (at = 0, n = 4, f0 = 420, v = .5) => { for (let i = 0; i < n; i++) tone(f0 - i * 18, .1, { type: "sine", v, at: at + i * .11, to: f0 * .6, a: .01, lp: 900 }); noise(n * .11 + .1, { f0: 900, type: "lowpass", v: .16, at, a: .05 }); };
  const clink = (at = 0, f = 3100, v = .4) => { tone(f, .35, { v, at, rev: .7, a: .001 }); tone(f * 1.5, .25, { v: v * .6, at: at + .004, rev: .7, a: .001 }); };
  const fizz = (at = 0, d = .7, v = .18) => noise(d, { f0: 6000, type: "highpass", v, at, a: .05, q: .4 });
  const brass = (notes, step, v = .55, type = "sawtooth", d = 1.7) => notes.forEach((f, i) => tone(f, step * d, { type, v, at: i * step, a: .02, lp: 2300, rev: .3 }));
  const splat = (at = 0, v = 1) => { noise(.3, { f0: 1000, f1: 180, q: .8, v: .9 * v, at, type: "lowpass", a: .004 }); tone(130, .2, { to: 55, v, at }); tone(520, .18, { to: 140, v: .35 * v, at }); noise(.15, { f0: 2500, f1: 800, q: 1.5, v: .35 * v, at: at + .03, a: .003 }); };
  const quack = (at = 0) => { tone(540, .16, { type: "sawtooth", to: 340, v: .5, at, lp: 1700, a: .01 }); tone(500, .14, { type: "sawtooth", to: 320, v: .45, at: at + .2, lp: 1700, a: .01 }); };
  const sparkle = (at = 0, base = 2093) => { arp([base, base * 1.26, base * 1.5, base * 2], .06, { d: .5, v: .5, type: "sine", at }); noise(.3, { f0: 8000, type: "highpass", v: .15, at: at + .15, a: .03 }); };
  const crunch = (at = 0) => { for (let i = 0; i < 3; i++) noise(.05, { f0: 1800 + i * 300, q: 1.2, v: .6, at: at + i * .09, a: .002 }); };
  const rustle = (at = 0, v = .3) => { for (let i = 0; i < 5; i++) noise(.06, { f0: 4200, type: "highpass", v: v * (.5 + Math.random() * .5), at: at + i * .05 + Math.random() * .03, a: .004 }); };
  const GS = {
    music_now: (at = 0) => { tone(320, .05, { type: "square", v: .4, at, lp: 1800 }); tone(200, .08, { v: .5, at: at + .06 }); arp([659, 784, 988], .08, { d: .25, v: .5 }); },
    music_queue: (at = 0) => { tone(1200, .03, { type: "square", v: .3, at }); tone(880, .12, { v: .5, at: at + .05, type: "triangle" }); tone(1175, .16, { v: .5, at: at + .13, type: "triangle" }); },
    crown1: (at = 0) => { brass([523, 659, 784, 1046], .1, .5); sparkle(.35, 2093); },
    crown2: (at = 0) => { brass([392, 523, 659, 784, 1046], .09, .55); noise(.7, { f0: 7000, type: "highpass", v: .2, at: .4, a: .02 }); tone(262, 1.1, { v: .45, at: .45, rev: .5 }); },
    king: (at = 0) => { brass([262, 330, 392, 523], .14, .6, "square"); tone(131, .9, { type: "sawtooth", v: .35, at: .5, lp: 500 }); },
    queen: (at = 0) => { arp([784, 988, 1175, 1568, 1976], .08, { d: .7, v: .6, type: "sine" }); sparkle(.45, 2637); },
    medal: (at = 0) => { tone(2637, .5, { v: .6, rev: .5, a: .002 }); tone(3951, .35, { v: .3, at: .01, rev: .5 }); brass([784, 1046], .12, .35, "triangle"); },
    trophy: (at = 0) => { brass([523, 659, 784, 1046, 1318], .1, .6); noise(.9, { f0: 2500, q: .3, v: .28, at: .35, a: .12 }); tone(262, 1.2, { v: .5, at: .5, rev: .6 }); },
    batcrown: (at = 0) => { tone(300, .45, { type: "sawtooth", to: 1500, v: .45, lp: 3000, a: .02 }); for (let i = 0; i < 4; i++) noise(.07, { f0: 600, type: "lowpass", v: .5, at: .1 + i * .09 }); tone(160, .6, { type: "sawtooth", v: .4, at: .45, lp: 400 }); },
    joker: (at = 0) => { tone(260, .35, { to: 900, v: .6, a: .01 }); tone(900, .3, { to: 260, v: .6, at: .35 }); tone(180, .12, { type: "square", v: .4, at: .7, lp: 900 }); tone(180, .12, { type: "square", v: .4, at: .85, lp: 900 }); },
    tophat: (at = 0) => { arp([392, 523, 659], .1, { d: .3, v: .6, type: "triangle" }); tone(784, .6, { v: .6, at: .3, type: "triangle", rev: .4 }); tone(988, .6, { v: .4, at: .3, type: "triangle", rev: .4 }); },
    sombrero: (at = 0) => { brass([659, 659, 784, 988, 784, 988], .1, .5, "square", 1.2); },
    viking: (at = 0) => { tone(130, 1, { type: "sawtooth", v: .55, lp: 650, a: .12, to: 150 }); tone(196, 1, { type: "sawtooth", v: .35, lp: 700, a: .15 }); },
    pirate: (at = 0) => { tone(110, .35, { type: "sawtooth", v: .5, lp: 500, a: .03, to: 85 }); tone(98, .35, { type: "sawtooth", v: .5, lp: 500, a: .03, at: .4, to: 80 }); tone(1300, .18, { type: "sawtooth", to: 700, v: .35, at: .85, lp: 2500 }); },
    propeller: (at = 0) => { tone(180, .8, { type: "sawtooth", to: 1300, v: .35, lp: 2500, a: .05 }); noise(.8, { f0: 400, f1: 3000, q: .6, v: .25, a: .05 }); tone(1300, .2, { to: 400, v: .3, at: .8 }); },
    leaf: (at = 0) => rustle(at, .4),
    wreath: (at = 0) => arp([988, 1175, 1319], .12, { d: .6, v: .5, type: "sine" }),
    basket: (at = 0) => { tone(320, .07, { type: "triangle", v: .7, at, to: 220 }); tone(300, .07, { type: "triangle", v: .6, at: at + .12, to: 200 }); rustle(at + .2, .15); },
    lips: (at = 0) => { noise(.07, { f0: 2600, f1: 900, q: 2, v: .8, at, a: .003 }); tone(1400, .09, { to: 520, v: .7, at }); noise(.05, { f0: 3500, q: 3, v: .5, at: at + .09 }); },
    gem: (at = 0) => sparkle(at, 2349),
    strawberry: (at = 0) => { crunch(at); tone(520, .25, { to: 440, v: .25, at: at + .35, type: "triangle" }); },
    tomato: (at = 0) => splat(at),
    frog: (at = 0) => { tone(110, .1, { type: "sawtooth", to: 230, v: .5, at, lp: 600 }); tone(120, .1, { type: "sawtooth", to: 260, v: .5, at: at + .13, lp: 600 }); splat(at + .3, .5); },
    rose: (at = 0) => { arp([659, 784, 988, 1319], .1, { d: .7, v: .55, type: "sine" }); tone(330, 1, { v: .25, at: .1, rev: .6 }); },
    candy: (at = 0) => { for (let i = 0; i < 6; i++) noise(.03, { f0: 5000 + Math.random() * 3000, type: "highpass", v: .5, at: at + i * .035 + Math.random() * .02, a: .002 }); tone(1760, .25, { v: .4, at: at + .3, rev: .4 }); },
    duck: (at = 0) => quack(at),
    pig: (at = 0) => { tone(190, .14, { type: "sawtooth", to: 135, v: .5, at, lp: 900 }); tone(250, .2, { type: "sawtooth", to: 160, v: .5, at: at + .17, lp: 900 }); },
    penguin: (at = 0) => { tone(420, .18, { type: "square", to: 300, v: .35, at, lp: 1300 }); tone(450, .16, { type: "square", to: 320, v: .35, at: at + .22, lp: 1300 }); tone(380, .22, { type: "square", to: 280, v: .35, at: at + .42, lp: 1300 }); },
    tulip: (at = 0) => arp([784, 988], .1, { d: .5, v: .5, type: "triangle" }),
    bouquet: (at = 0) => arp([523, 659, 784, 988, 1175, 1568], .07, { d: .7, v: .5, type: "sine" }),
    plant: (at = 0) => { rustle(at, .25); tone(400, .1, { to: 700, v: .4, at: at + .25, type: "triangle" }); },
    cactus: (at = 0) => { noise(.03, { f0: 4000, type: "highpass", v: .7, at }); tone(700, .25, { to: 280, v: .5, at: at + .05, type: "triangle" }); },
    icecream: (at = 0) => { noise(.35, { f0: 800, f1: 2800, q: 1.5, v: .3, at, a: .05 }); tone(600, .3, { to: 1000, v: .3, at: at + .1, type: "sine" }); tone(1318, .3, { v: .4, at: at + .4, rev: .4 }); },
    cake: (at = 0) => { arp([523, 659, 784, 1046], .09, { d: .4, v: .55, type: "triangle" }); tone(2093, .5, { v: .3, at: .4, rev: .6 }); },
    milk: (at = 0) => glug(at, 5, 400, .55),
    wine: (at = 0) => { glug(at, 3, 380, .5); clink(at + .5); },
    whisky: (at = 0) => { glug(at, 3, 330, .5); clink(at + .35, 2700, .45); clink(at + .5, 2500, .35); },
    blackrose: (at = 0) => { arp([392, 466, 587, 698], .13, { d: .8, v: .5, type: "triangle" }); tone(98, 1, { v: .3, at: .1, lp: 400 }); },
    ring: (at = 0) => { tone(3136, .7, { v: .5, rev: .6, a: .001 }); tone(4699, .5, { v: .25, at: .01, rev: .6 }); sparkle(.2, 2637); },
    dice: (at = 0) => { for (let i = 0; i < 7; i++) { tone(1400 + Math.random() * 900, .03, { type: "square", v: .35, at: at + i * .05 + Math.random() * .02, lp: 3000 }); noise(.03, { f0: 2500, v: .4, at: at + i * .05, a: .002 }); } tone(900, .12, { v: .4, at: at + .42, type: "triangle" }); },
    cocktail: (at = 0) => { glug(at, 3, 450, .45); fizz(at + .1, .6, .15); clink(at + .55, 3400, .3); },
    martini: (at = 0) => { clink(at, 3300, .5); glug(at + .25, 2, 420, .4); clink(at + .6, 3600, .3); },
    champagne: (at = 0) => { noise(.08, { f0: 700, q: .8, v: .95, at, a: .002 }); tone(320, .12, { to: 80, v: .9, at }); fizz(at + .06, 1, .3); clink(at + .8, 3000, .35); },
    diamondring: (at = 0) => { tone(3520, .9, { v: .55, rev: .7, a: .001 }); tone(5274, .6, { v: .3, at: .01, rev: .7 }); sparkle(.25, 3136); sparkle(.5, 3951); },
    tea: (at = 0) => { glug(at, 3, 360, .4); clink(at + .5, 2200, .35); tone(1760, .5, { v: .15, at: at + .55, rev: .6 }); },
    cola: (at = 0) => { noise(.06, { f0: 3000, q: 1, v: .7, at, a: .002 }); fizz(at + .05, .9, .3); glug(at + .5, 3, 480, .35); },
    smoothie: (at = 0) => { noise(.5, { f0: 1500, f1: 3000, q: 2, v: .22, at, a: .05 }); glug(at + .35, 3, 520, .4); },
    egg: (at = 0) => { tone(900, .02, { type: "square", v: .5, at }); noise(.05, { f0: 3000, q: 2, v: .7, at: at + .03, a: .002 }); noise(.05, { f0: 2200, q: 2, v: .6, at: at + .1, a: .002 }); splat(at + .18, .5); },
  };
  const gsound = (e, at = 0) => { const id = (typeof GIFT_BY_EMOJI !== "undefined" && GIFT_BY_EMOJI[e]) || e; const f = GS[id]; if (!f) return false; if (at > 0) setTimeout(() => f(0), at * 1000); else f(0); return true; };

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
      if (!ready()) return; if (gsound(e, at)) return; const k = giftKind(e);
      if (k === "splat") { noise(.22, { f0: 700, f1: 160, q: .7, v: .9, at, type: "lowpass" }); tone(130, .18, { to: 60, v: .9, at }); }
      else if (k === "drink") { tone(2400, .25, { v: .45, at, rev: .6 }); tone(3100, .18, { v: .3, at: at + .03, rev: .6 }); noise(.5, { f0: 5000, type: "highpass", v: .2, at: at + .05, a: .1 }); }
      else if (k === "jewel") arp([1319, 1568, 2093, 2637], .06, { d: .45, v: .55 });
      else if (k === "royal") arp([523, 659, 784, 1046], .09, { d: .5, v: .8, type: "square" });
      else if (k === "flower") arp([659, 784, 988], .09, { d: .6, v: .6, type: "sine" });
      else if (k === "cute") { tone(900, .08, { to: 1400, v: .6, at }); tone(1400, .09, { to: 900, v: .6, at: at + .09 }); }
      else arp([740, 1110], .08, { d: .35, v: .7 });
    },
    giftGot: e => { if (!ready()) return; haptic("ok"); tone(1318, .16, { v: .45, type: "triangle" }); api.giftHit(e, .12); },
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
    giftIds: () => Object.keys(GS),
    giftPlay: id => { if (ready()) GS[id] && GS[id](0); },
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
