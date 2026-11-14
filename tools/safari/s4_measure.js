
(function () { const b = [...document.querySelectorAll('button')].find(x => /Hear this measure/.test(x.textContent));
  const before = { had: !!AC, state: AC ? AC.state : null }; b.click();
  const right = { state: AC.state, ct: AC.currentTime, ring: b.classList.contains('sounding'), active: !!(navigator.userActivation && navigator.userActivation.isActive) };
  sounded(4.5).then(s => { R['measure'] = Object.assign({ before, right, stateAfter: AC.state, ctAfter: +AC.currentTime.toFixed(2) }, s); out('next'); }); })(); 0;
