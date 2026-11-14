"""The page's own script (choral/app.html), where it can be run by itself: the reckoning that needs no browser.

Each function is taken out of the page as it is written there and run with node where there is one (GitHub's
machines have it) or with the Mac's own JavaScript (osascript); where there is neither, these are skipped.  What
needs a browser - a click, a sound, a track playing - is tried by hand in a copy of the page."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

from choral import app

HTML = open(os.path.join(os.path.dirname(app.__file__), 'app.html'), encoding='utf-8').read()


def source(name):
    """One of the page's functions, as text: from "function name(" to the brace that closes it."""
    start = HTML.index('function ' + name + '(')
    depth, i = 0, HTML.index('{', start)
    while True:
        depth += {'{': 1, '}': -1}.get(HTML[i], 0)
        if depth == 0:
            return HTML[start:i + 1]
        i += 1


def js(expression, *functions, consts=(), before=''):
    """The value of a JavaScript expression that uses the page's functions (and its constants) named.
    before: JavaScript of the test's own, put ahead of them - a stand-in for what a browser would provide."""
    lines = [before] + [next(ln for ln in HTML.splitlines() if ln.startswith('const ' + c + ' =')) for c in consts] + [source(f) for f in functions]
    value = 'JSON.stringify(' + expression + ')'
    if shutil.which('node'):                             # as a file: nothing of it has to survive a command line
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, 'page.js')
            with open(f, 'w', encoding='utf-8') as o:
                o.write('\n'.join(lines) + '\nconsole.log(' + value + ')\n')
            r = subprocess.run([shutil.which('node'), f], capture_output=True, text=True, encoding='utf-8', timeout=60)
    elif sys.platform == 'darwin' and shutil.which('osascript'):
        r = subprocess.run(['osascript', '-l', 'JavaScript', '-e', '\n'.join(lines) + '\n' + value], capture_output=True, text=True, encoding='utf-8', timeout=60)
    else:
        pytest.skip('nothing on this computer runs JavaScript by itself')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# when each measure begins in a track: [seconds, the measure's number], in the order played
PLAIN = [[1.0, 0], [1.6, 1], [4.0, 2], [6.4, 3], [8.8, 4]]              # an upbeat, then four measures
TWICE = [[0, 1], [2, 2], [4, 1], [6, 2], [8, 3]]                         # measures 1 and 2 are repeated


# ---- the measure being heard
@pytest.mark.parametrize('seconds, measure', [(0, 0), (1.2, 0), (1.56, 1), (3.9, 1), (4.0, 2), (99, 4)])
def test_the_measure_at_a_moment(seconds, measure):
    assert js(f'measureAt({{timeline: {PLAIN}}}, {seconds})', 'measureAt') == measure


def test_a_track_that_does_not_know_its_measures_has_none():
    assert js('measureAt({}, 3)', 'measureAt') is None


@pytest.mark.parametrize('measures, said', [([7], 'measure 7'), ([0, 1, 2, 3, 4, 7, 9], 'measures 0\u20134, 7 and 9'), ([3, 4], 'measures 3\u20134'), ([2, 5], 'measures 2 and 5')])
def test_measures_said_in_words(measures, said):
    assert js(f'runs({measures})', 'runs') == said


# ---- a passage to repeat: from the beginning of one measure to the end of another
def stretch(tl, a, b):
    return js(f'stretch({tl}, {a}, {b})', 'stretch')


def test_a_passage_runs_from_the_start_of_its_first_measure_to_the_end_of_its_last():
    assert stretch(PLAIN, 1, 2) == {'from': 1.6, 'to': 6.4}
    assert stretch(PLAIN, 3, 3) == {'from': 6.4, 'to': 8.8}             # one measure, over and over
    assert stretch(PLAIN, 0, 1) == {'from': 1.0, 'to': 4.0}             # from the pickup


def test_a_passage_to_the_last_measure_runs_to_the_end_of_the_track():
    assert stretch(PLAIN, 3, 4) == {'from': 6.4, 'to': None}


def test_measures_given_the_wrong_way_round_are_taken_the_right_way():
    assert stretch(PLAIN, 3, 1) == stretch(PLAIN, 1, 3) == {'from': 1.6, 'to': 8.8}


def test_a_measure_the_piece_has_not_is_named():
    assert stretch(PLAIN, 2, 9) == {'missing': 9}
    assert stretch(PLAIN, 7, 2) == {'missing': 7}


def test_in_a_piece_with_a_repeat_the_passage_is_the_shortest_that_fits():
    assert stretch(TWICE, 1, 2) == {'from': 0, 'to': 4}                 # the first time through
    assert stretch(TWICE, 2, 3) == {'from': 6, 'to': None}              # the 2 that leads on to 3: the second
    assert stretch(TWICE, 2, 1) == {'from': 2, 'to': 6}                 # over the repeat itself: 2, and back to 1


# ---- slower, for learning
@pytest.mark.parametrize('kept, speed', [('0.7', .7), ('1', 1), ('0.5', .5), (None, 1), ('', 1), ('3', 1), ('fast', 1), ('0.71', 1)])
def test_only_the_speeds_offered_are_ever_used(kept, speed):
    assert js(f'speedOf({json.dumps(kept)})', 'speedOf', consts=['SPEEDS']) == speed


def test_the_speeds_offered_begin_with_the_tempo_as_written_and_only_go_slower():
    speeds = js('SPEEDS.map(s => s[0])', consts=['SPEEDS'])
    assert speeds[0] == 1 and speeds == sorted(speeds, reverse=True) and min(speeds) >= .5


# ---- the fixer's own sound: what the page does with a sound output that is slow, or stuck
# A browser's sound output is asleep when it is made; it wakes only if asked inside a click; and it may take its time
# about it - headphones that have to be woken, a computer busy making tracks.  This stands in for one: START is how
# many milliseconds it takes to begin once asked (Infinity: it never does), GESTURE is whether a click is under way.
BROWSER = """
var NOW = 0, TIMERS = [], GESTURE = false, MADE = [], START = 0, PAINTED = 0;
function setTimeout(fn, ms) { TIMERS.push({ at: NOW + ms, fn: fn }); return TIMERS.length; }
function clearTimeout() {}
function pass(ms) { var end = NOW + ms; for (;;) { TIMERS.sort(function (a, b) { return a.at - b.at; }); var t = TIMERS[0]; if (!t || t.at > end) break; TIMERS.shift(); NOW = t.at; t.fn(); } NOW = end; }
function Output() { this.inClick = GESTURE; this.closed = false; this.asked = null; this.lag = 0; this.notes = 0; MADE.push(this); }
Object.defineProperty(Output.prototype, 'state', { get: function () { return this.closed ? 'closed' : this.asked != null && NOW >= this.asked + this.lag ? 'running' : 'suspended'; } });
Object.defineProperty(Output.prototype, 'currentTime', { get: function () { return this.state === 'running' ? (NOW - this.asked - this.lag) / 1000 : 0; } });
Output.prototype.resume = function () { if (GESTURE && this.asked == null) { this.asked = NOW; this.lag = START; } return { catch: function () {} }; };
Output.prototype.close = function () { this.closed = true; };
var window = { AudioContext: Output }, AC = null, fixing = { piece: { msg: '' } };
function paintFixer() { PAINTED++; }
function tone() { AC.notes++; }
function click() { GESTURE = true; try { play('piece', function (t0) { tone(60, t0, .5); return .5; }); } finally { GESTURE = false; } }
function told() { return fixing.piece.msg === NO_SOUND; }
function outputs() { return MADE.map(function (o) { return { inClick: o.inClick, closed: o.closed, state: o.state, notes: o.notes }; }); }
"""


def sound_page(script):
    return js('(function () { ' + script + ' })()', 'sound', 'play', consts=['NO_SOUND'], before=BROWSER)


def test_an_output_slow_to_start_is_waited_for_not_thrown_away():
    # Heard as "the play button has stopped working": the page gave the output under a second to begin, then threw
    # it away and made another - and with headphones that take two seconds to wake, did so at every click, for ever.
    got = sound_page('START = 2000; click(); pass(10000); return { outputs: outputs(), told: told() };')
    assert got == {'outputs': [{'inClick': True, 'closed': False, 'state': 'running', 'notes': 1}], 'told': False}


def test_no_output_is_ever_made_outside_a_click():
    # (a browser will not wake one that is: it would sit there silent, in place of one that worked)
    got = sound_page('START = 2000; click(); pass(900); click(); pass(1500); click(); pass(20000); START = Infinity; click(); pass(20000); click(); pass(20000); return outputs();')
    assert got and all(o['inClick'] for o in got)


def test_a_second_click_while_it_is_still_starting_uses_the_same_output():
    got = sound_page('START = 2000; click(); pass(500); click(); pass(10000); return { outputs: outputs(), told: told() };')
    assert got == {'outputs': [{'inClick': True, 'closed': False, 'state': 'running', 'notes': 2}], 'told': False}


def test_an_output_that_never_starts_is_said_and_made_anew_at_the_next_click():
    got = sound_page("""START = Infinity; click(); pass(10000); var first = { told: told(), made: MADE.length, closed: MADE[0].closed };
                        START = 50; click(); pass(10000); return { first: first, outputs: outputs(), told: told() };""")
    assert got['first'] == {'told': True, 'made': 1, 'closed': False}             # said, and nothing done behind the listener's back
    assert got['outputs'] == [{'inClick': True, 'closed': True, 'state': 'closed', 'notes': 1},
                              {'inClick': True, 'closed': False, 'state': 'running', 'notes': 1}]
    assert got['told'] is False                                                    # it sounds again: the sentence goes


def test_an_output_that_started_late_after_all_is_kept():
    # seven seconds to wake: the page has said there was no sound by then - but it is running at the next click
    got = sound_page('START = 7000; click(); pass(6000); var said = told(); pass(4000); click(); pass(10000); return { said: said, outputs: outputs(), told: told() };')
    assert got == {'said': True, 'outputs': [{'inClick': True, 'closed': False, 'state': 'running', 'notes': 2}], 'told': False}


def test_an_output_that_works_is_left_alone():
    got = sound_page('START = 30; click(); pass(3000); click(); pass(10000); return { outputs: outputs(), told: told(), painted: PAINTED };')
    assert got == {'outputs': [{'inClick': True, 'closed': False, 'state': 'running', 'notes': 2}], 'told': False, 'painted': 0}


# ---- the little singer: what its mouth is doing at a moment of a track
NOTES = [[1.0, 1.0, 'a'], [2.0, 1.0, 'e'], [3.0, 0.5, 'o'], [5.0, 2.0, 'm'], [8.0, 1.0, 'a']]      # [begins, lasts, mouth]


def mouth_at(t, notes=NOTES):
    return js(f'mouthAt({json.dumps(notes)}, {t})', 'mouthAt')


def test_the_mouth_is_shut_before_the_first_note_between_phrases_and_after_the_last():
    for t in (0, 0.9, 3.8, 4.5, 7.5, 9.5, 60):
        assert mouth_at(t)[0] == 0, t
    assert mouth_at(4)[1] is None                       # and it is no vowel's mouth then


def test_the_mouth_opens_quickly_on_a_note_and_is_that_vowels():
    opened, mouth, since, _ = mouth_at(1.5)
    assert opened == 1 and mouth == 'a' and since == pytest.approx(.5)
    assert 0 < mouth_at(1.02)[0] < 1                    # opening: not a switch thrown
    assert mouth_at(2.5)[1] == 'e' and mouth_at(3.2)[1] == 'o'


def test_the_mouth_stays_open_from_one_note_to_the_next_and_closes_at_the_end_of_a_phrase():
    assert mouth_at(1.98)[0] == 1                       # "la" runs straight into "see": no shutting between
    assert 0 < mouth_at(3.46)[0] < 1                    # the last note before a rest: closing
    assert mouth_at(3.49)[0] < mouth_at(3.44)[0]


def test_a_hum_is_sung_with_the_lips_together():
    opened, mouth, _, _ = mouth_at(6)
    assert opened == 0 and mouth == 'm'


def test_no_notes_no_mouth():
    assert mouth_at(3, [])[0] == 0 and js('mouthAt(null, 3)', 'mouthAt')[0] == 0


# ---- whose notes the singer sings beside a track
SING = {'parts': {'T1': [[1, 1, 'a']], 'BR': [[1, 1, 'o']], 'BS': [[1, 1, 'e']]}, 'all': [[1, 1, 'a']], 'labels': {'Tenor 1': 'T1', 'Baritone': 'BR', 'Bass': 'BS'}}
PIECE = {'read': {'parts': [['tenor1', 'Tenor 1'], ['baritone', 'Baritone'], ['bass', 'Bass']]}, 'made': {'part': 'baritone'}}


@pytest.mark.parametrize('file, piece, part', [
    ('My Song - Bass predominant.m4a', PIECE, 'BS'),                 # the part the track is named for,
    ('Bass/My Song - Bass alone.mp3', PIECE, 'BS'),                  # (in a set made for the whole chorus)
    ('My Song - Tenor 1 muted.m4a', PIECE, 'T1'),                    # ... also where it is left out: it shows when to sing
    ('My Song - balanced.m4a', PIECE, 'BR'),                         # the part the tracks were made for,
    ('My Song - voices only.m4a', dict(PIECE, made={'part': 'all'}), 'all'),      # or the whole choir
    ('My Song - Alto predominant.m4a', PIECE, 'all'),                # a part nobody knows: whoever is singing
    ('My Song - balanced.m4a', {}, 'all'),
])
def test_the_singer_sings_the_part_the_track_is_for(file, piece, part):
    assert js(f'singerPart({json.dumps(file)}, {json.dumps(piece)}, {json.dumps(SING)})', 'singerPart') == part


# ---- the singers are not all one colour
# The first figure had a single cream head and hands, meant as "neutral".  A listener asked why all the little
# people were white - which is what one pale tone for everybody is.  Each track's singer now has a skin tone of
# its own, from a range that runs from deep brown to light.
def tones():
    return js('TONES', consts=['TONES'])


def brightness(rgb):
    return .2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2]


def test_the_singers_skin_tones_run_from_deep_to_light():
    t = tones()
    assert len(t) >= 6
    light = [brightness(c) for c in t]
    assert min(light) < .25 and max(light) > .75                   # really deep, and really light
    assert sum(b < .5 for b in light) >= len(t) // 2               # and the darker half is not a token one
    assert all(c[0] > c[1] > c[2] for c in t)                      # skin: warm, every one of them


def test_the_tracks_of_a_piece_have_singers_of_different_tones():
    n = len(tones())
    got = [js(f'singerTone("My Song", {i})', 'singerTone', consts=['TONES']) for i in range(n)]
    assert sorted(got) == list(range(n))                           # as many different singers as there are tones
    assert all(abs(a - b) > 1 for a, b in zip(got, got[1:]))       # and the track below is not the next shade along


def test_a_singer_keeps_its_tone_and_pieces_do_not_all_begin_alike():
    assert js('singerTone("My Song", 2)', 'singerTone', consts=['TONES']) == js('singerTone("My Song", 2)', 'singerTone', consts=['TONES'])
    firsts = {js(f'singerTone({json.dumps(name)}, 0)', 'singerTone', consts=['TONES']) for name in ('My Song', 'Another', 'A Third One', 'Fourth', 'The Fifth Piece', 'Six')}
    assert len(firsts) >= 3
    assert js('singerTone("My Song", -1)', 'singerTone', consts=['TONES']) in range(len(tones()))       # a track it cannot place still gets one


# ---- the mouth as a choir is taught it: the vowel held, a diphthong turned late, a consonant closed at the last moment
def test_a_diphthong_is_its_first_vowel_and_turns_only_at_the_very_end():
    my = [[1.0, 1.0, 'a', 'i', '', .5], [2.0, 1.0, 'u', '', '', .5]]
    assert mouth_at(1.3, my)[1] == 'a' and mouth_at(1.8, my)[1] == 'a'      # "mah..." nearly all the way
    assert mouth_at(1.95, my)[1] == 'i'                                     # "...ee", just before the next note
    assert mouth_at(2.3, my)[1] == 'u'


def test_a_last_consonant_closes_the_mouth_at_the_end_of_its_note():
    night = [[1.0, 1.0, 'a', 'i', 't', .5]]
    assert mouth_at(1.5, night)[1] == 'a'
    opened, shape, _, _ = mouth_at(1.985, night)
    assert shape == 't' and opened < .5                                     # the tongue, where the note stops
    come = [[1.0, .5, 'a', '', 'b', .5], [1.5, .5, 'a', '', '', .5]]        # ... also when the next note follows at once
    assert mouth_at(1.48, come)[1] == 'b' and mouth_at(1.48, come)[0] == 0  # lips together for "m"
    assert mouth_at(1.6, come)[1] == 'a'


def test_how_high_the_note_lies_comes_with_the_mouth():
    assert mouth_at(1.5, [[1.0, 1.0, 'a', '', '', .9]])[3] == .9
    assert mouth_at(1.5)[3] == .5                                           # (not said: the middle)


# ---- when to breathe
BREATHS = [[5.0, 'b', 1.0], [8.0, 'c', .25], [10.0, 's', 16.0], [30.0, 'b', .3]]      # [the moment to have breathed by, kind, room]


def breath_at(t, breaths=BREATHS):
    return js(f'breathAt({json.dumps(breaths)}, {t})', 'breathAt')


def test_a_breath_is_taken_in_the_beat_before_an_entrance():
    assert breath_at(3.0) == [0, None, False]                               # too early
    filling, kind, _ = breath_at(4.55)
    assert kind == 'b' and filling == pytest.approx(.5, abs=.02)            # half way in, with .9 s to take it
    assert breath_at(4.99)[0] > .95 and breath_at(5.0)[0] == 0              # full - and then it is sung


def test_a_breath_has_no_more_time_than_the_rest_gives_it():
    assert breath_at(29.6)[0] == 0 and breath_at(29.85)[0] == pytest.approx(.5, abs=.02)


def test_a_catch_breath_is_quick():
    assert breath_at(7.7)[0] == 0
    filling, kind, _ = breath_at(7.9)
    assert kind == 'c' and .4 < filling < .8


def test_a_long_stretch_is_one_to_stagger_the_breathing_in():
    assert breath_at(12)[2] is True and breath_at(9.5)[2] is False and breath_at(26.5)[2] is False
    assert breath_at(3, [])[0] == 0 and js('breathAt(null, 3)', 'breathAt') == [0, None, False]
