
(function () { const a = cards[S.pieces[0].id].node.querySelector('audio'); a.volume = .01; a.currentTime = 3.6;      // (where the choir comes in)
  a.play().then(async () => { await wait(1500); const tr = a.closest('.track');
    R.track = { played: +(a.currentTime - 3.6).toFixed(2), rate: a.playbackRate };
    R.singer = { on: singer.on, beside: !!tr.querySelector('canvas.singer'), notes: singer.notes ? singer.notes.length : 0, open: +singer.s.open.toFixed(2), why: singer.why || null };
    a.pause(); out('next'); }, e => { R.track = { error: String(e) }; out('next'); }); })(); 0;
