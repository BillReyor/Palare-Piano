
(function () { const a = cards[S.pieces[0].id].node.querySelector('audio'); a.volume = .01;
  a.play().then(async () => { await wait(1500); R.track = { played: +a.currentTime.toFixed(2), rate: a.playbackRate }; a.pause(); out('next'); }, e => { R.track = { error: String(e) }; out('next'); }); })(); 0;
