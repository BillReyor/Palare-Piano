
(async function () { try { await openFixer(S.pieces[0], null, 2); await wait(600); out('next'); } catch (e) { out({ error: 's3 ' + e }); } })(); 0;
