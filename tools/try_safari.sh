#!/bin/sh
# The page, tried in Safari's own engine (on a Mac; it needs the Swift compiler that comes with Xcode's tools).
#
#     sh tools/try_safari.sh
#
# Safari is what the page opens in on most Macs, and it is strict about sound in ways the other browsers are not.
# For a while every trial of the page was made in a browser of the other family, because that is what the tools at
# hand could drive; two "fixes" to the fixer's sound were made that way, and neither was a fix.  This opens the real
# page in a small window built on Safari's engine, with a copy of the program serving it from an empty library made
# for the purpose, and does what a singer does: makes tracks for the demo piece, plays one (and looks whether the
# little singer beside it sings), opens "Fix a note or a word" and presses "Hear this measure" and "Hear this line".  It listens where the sound leaves the page - turned
# down so far that the room hears nothing - and says whether the notes were there.
#
# What it cannot tell: whether a person hears them.  A muted tab, a muted computer, a setting of Safari itself are
# beyond the page, and beyond this.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ "$(uname -s)" = "Darwin" ] || { echo "try_safari.sh is for a Mac: Safari's engine is only there." >&2; exit 2; }
command -v swiftc >/dev/null 2>&1 || { echo "It needs the Swift compiler: install Xcode's command line tools (xcode-select --install)." >&2; exit 2; }
PY="$ROOT/.venv-test/bin/python"
[ -x "$PY" ] || sh "$ROOT/tools/test.sh" --collect-only >/dev/null
PORT=8794
WORK="$(mktemp -d)"
SERVER=""
ended() { code=$?; [ -z "$SERVER" ] || kill "$SERVER" 2>/dev/null || true; rm -rf "$WORK"; exit "$code"; }
trap ended EXIT

swiftc -O "$ROOT/tools/safari/window.swift" -o "$WORK/window" 2>"$WORK/build.log" || { cat "$WORK/build.log" >&2; exit 1; }
mkdir "$WORK/library"
( cd "$ROOT" && PALARE_LIBRARY="$WORK/library" PALARE_PORT="$PORT" PALARE_NO_BROWSER=1 PALARE_NO_OPEN=1 PALARE_QUIET=1 exec "$PY" -m choral.app ) >"$WORK/server.log" 2>&1 &
SERVER=$!
n=0; until curl -s -o /dev/null "http://127.0.0.1:$PORT/" || [ "$n" -ge 40 ]; do sleep .25; n=$((n + 1)); done

echo "Making tracks for the demo piece and using the page in Safari's engine (about a minute; a small window opens)..."
"$WORK/window" "http://127.0.0.1:$PORT/" "$ROOT"/tools/safari/s?_*.js show >"$WORK/said.txt" 2>&1 || { echo "The window did not finish:" >&2; tail -5 "$WORK/said.txt" >&2; exit 1; }
tail -1 "$WORK/said.txt" | "$PY" "$ROOT/tools/safari/check.py"
