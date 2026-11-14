window.out = msg => window.webkit.messageHandlers.out.postMessage(typeof msg === 'string' ? msg : JSON.stringify(msg)); window.wait = ms => new Promise(r => setTimeout(r, ms));

window.R = {}; window.LOG = [];
(async function () { try {
  const Real = window.AudioContext || window.webkitAudioContext;
  window.AudioContext = function () {
    const c = new Real(), tap = c.createGain(), quiet = c.createGain(), sp = c.createScriptProcessor(1024, 1, 1), real = c.destination;
    quiet.gain.value = .003; tap.connect(quiet); quiet.connect(real); tap.connect(sp); sp.connect(real);      // heard by the test, not by the room
    sp.onaudioprocess = e => { const d = e.inputBuffer.getChannelData(0); let s = 0; for (let i = 0; i < d.length; i++) s += d[i] * d[i]; LOG.push([e.playbackTime, Math.sqrt(s / d.length)]); };
    Object.defineProperty(c, 'destination', { value: tap });
    return c;
  };
  window.sounded = async secs => { const n0 = LOG.length; await wait(secs * 1000); const b = LOG.slice(n0); return { blocks: b.length, withSound: b.filter(x => x[1] > 1e-4).length, peak: +b.reduce((m, x) => Math.max(m, x[1]), 0).toFixed(4) }; };
  await wait(1500); await refresh();
  if (!S.pieces.length) { await post('/api/demo'); for (let i = 0; i < 30; i++) { await wait(700); await refresh(); if (S.pieces[0] && S.pieces[0].status === 'read') break; } }
  if (S.pieces[0].status !== 'ready') { await post('/api/render', { id: S.pieces[0].id, part: 'bass', singers: 4 }); for (let i = 0; i < 100; i++) { await wait(1000); await refresh(); if (S.pieces[0].status === 'ready' && !S.job) break; } }
  await wait(800); R.ua = navigator.userAgent; R.status = S.pieces[0].status; out('next');
} catch (e) { out({ error: 's1 ' + e }); } })(); 0;
