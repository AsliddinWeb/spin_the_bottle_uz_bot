// Opens every window and reports what does not fit the screen. Dev page: load this file, join a table with other players, run: await window.__fit()
// Expected result: {} (the wheel's pointer sticking out on the left is intended).
window.__fit = async function () {
  const wait = ms => new Promise(r => setTimeout(r, ms)), vw = innerWidth, vh = innerHeight, out = {};
  const other = T.seats.find(s => s.uid !== ME.id), clear = () => { document.querySelectorAll('#modal-root > *').forEach(e => e.remove()); ['#gift-panel', '#gest-panel', '#bottle-panel'].forEach(s => document.querySelector(s).classList.add('hidden')); };
  const windows = {
    shop: () => openShop(), vip: () => openVip(), free: () => openFree(), promo: () => openPromo(), compl: () => openComplTask(), wheel: () => openWheel(), chance: () => openChanceShop(() => {}),
    rating: () => openRatings(), menu: () => openMenu(), ach: () => openAchievements(), boosters: () => openBoosters(), league: () => openLeague(), frames: () => openStore('frame'), bottle: () => openBottlePanel(),
    settings: () => openSettings(), tables: () => openTables(), profileMe: () => openProfile(ME.id), profileOther: () => openProfile(other.uid), gifts: () => openGifts(other.uid), gestures: () => openGestures(),
    daily: () => openDailyTasks(), starter: () => openStarter(), music: () => openMusicPicker('music_now', 'audio'), video: () => openMusicPicker('music_now', 'video'), profEdit: () => profileModal(false),
    pm: () => openPm({ id: other.uid, name: other.name }), kick: () => openKick({ id: other.uid, name: other.name }), report: () => openReport(other.uid),
  };
  const check = () => {
    const bad = [];
    const roots = [...document.querySelectorAll('#modal-root .modal, #modal-root .pop, #gift-panel:not(.hidden), #gest-panel:not(.hidden), #bottle-panel:not(.hidden)')];
    for (const m of roots) {
      const r = m.getBoundingClientRect(), st = getComputedStyle(m);
      if (r.left < -6 || r.right > vw + 6) bad.push(`wide ${Math.round(r.left)}..${Math.round(r.right)}`);
      if (r.top < -6 || r.bottom > vh + 6) bad.push(`tall ${Math.round(r.top)}..${Math.round(r.bottom)}`);
      if (m.scrollWidth > m.clientWidth + 3 && st.overflowX !== 'hidden') bad.push(`hscroll ${m.scrollWidth}>${m.clientWidth}`);
      if (m.classList.contains('modal') && m.scrollHeight > m.clientHeight + 3 && !/(auto|scroll)/.test(st.overflowY)) bad.push('cut-off height');
      for (const e of m.querySelectorAll('button, b, span, h2, h3, p, input, select, img, svg')) {
        const q = e.getBoundingClientRect(); if (!q.width || e.closest('.rays, .kfx, [aria-hidden]') && e.tagName !== 'BUTTON') continue;
        let clipped = false; for (let p = e.parentElement; p && p !== m; p = p.parentElement) if (/(auto|scroll|hidden)/.test(getComputedStyle(p).overflowX)) clipped = true;
        if (!clipped && (q.right > r.right + 8 || q.left < r.left - 8)) { bad.push(`child ${e.tagName}.${String(e.className.baseVal ?? e.className).split(' ')[0]} ${Math.round(q.left - r.left)}..${Math.round(q.right - r.left)}/${Math.round(r.width)}`); break; }
        if (e.tagName === 'BUTTON' && e.scrollWidth > e.clientWidth + 3 && getComputedStyle(e).overflow !== 'visible') { bad.push(`button text cut: ${e.textContent.trim().slice(0, 24)}`); break; }
      }
    }
    if (!roots.length) bad.push('did not open');
    return bad;
  };
  for (const [name, open] of Object.entries(windows)) {
    clear(); try { open(); } catch (e) { out[name] = 'error ' + e.message; continue; }
    await wait(650); document.getAnimations().forEach(a => { try { a.finish(); } catch {} }); await wait(60);
    const b = check(); if (b.length) out[name] = b;
  }
  clear();
  const page = []; if (document.documentElement.scrollWidth > vw) page.push('page scrolls sideways');
  const app = document.querySelector('#chat-form').getBoundingClientRect(); if (app.bottom > vh + 1) page.push('input row below screen ' + Math.round(app.bottom));
  if (document.querySelector('#chat').clientHeight < 60) page.push('chat area only ' + document.querySelector('#chat').clientHeight + 'px');
  for (const s of document.querySelectorAll('.seat:not(.empty) .av, .side .round, #btn-hearts')) { const q = s.getBoundingClientRect(); if (q.left < -2 || q.right > vw + 2) { page.push('table element off screen'); break; } }
  if (page.length) out.page = page;
  return out;
};
