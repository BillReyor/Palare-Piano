"""What tools/try_safari.sh's window reported (JSON on standard input) -> said in words; exit 1 if anything was not right."""
import json
import sys

r = json.loads(sys.stdin.read())
wrong = [r['error']] if r.get('error') else []
track, measure, line = r.get('track') or {}, r.get('measure') or {}, r.get('line') or {}
if not track.get('played', 0) > 1:
    wrong.append(f'a track did not play: {track}')
for name, x, least in (('Hear this measure', measure, 100), ('Hear this line', line, 50)):
    if not (x.get('right') or {}).get('ring'):
        wrong.append(f'{name}: the button did not show that it was sounding')
    if not x.get('withSound', 0) >= least:
        wrong.append(f"{name}: sound in {x.get('withSound')} of {x.get('blocks')} blocks (its output: {x.get('stateAfter')})")
singer = r.get('singer') or {}
if singer.get('on') and not (singer.get('beside') and singer.get('notes') and singer.get('open', 0) > .3):
    wrong.append(f'the little singer did not sing beside the track: {singer}')
if r.get('hidden'):
    print('  (the window counted as hidden: its clocks run slow and it is given no frames)')
if r.get('msg'):
    wrong.append('the page said: ' + r['msg'])
print(f"  a track played {track.get('played')} s; Hear this measure: sound in {measure.get('withSound')} of {measure.get('blocks')} blocks; "
      f"Hear this line: {line.get('withSound')} of {line.get('blocks')}; the little singer's mouth {singer.get('open')} open on {singer.get('notes')} notes")
for w in wrong:
    print('  NOT RIGHT:', w)
if not wrong:
    print("ALL RIGHT in Safari's engine.")
sys.exit(1 if wrong else 0)
