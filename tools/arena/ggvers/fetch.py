"""Sample ~N Greek Gift games per version and cache their replays as JSON."""
import json, os, random, sys, time, urllib.request, urllib.error
SP = "/private/tmp/claude-501/-Users-ernestogomez-Desktop-fog-of-war-chess-bots/3fff0c37-7c67-4dbf-bb0b-a74cc0916a1a/scratchpad/"
OUT = SP + "research/ggvers/replays/"
G = "f394d843d970454f868c38c7f6963cc9"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
VERS = [1, 2, 14, 16, 21, 25]
games = json.load(open(SP + "gg_all_games.json"))
rng = random.Random(20261119)
byv = {}
for g in games:
    v = g["whiteVersion"] if g["whitePlayerId"] == G else g["blackVersion"]
    byv.setdefault(v, []).append(g)
todo = []
for v in VERS:
    gs = byv[v][:]
    rng.shuffle(gs)
    todo += gs[:N]
print("to fetch", len(todo), flush=True)
done = 0
for g in todo:
    path = OUT + g["id"] + ".json"
    if os.path.exists(path):
        continue
    for attempt in range(6):
        try:
            r = urllib.request.urlopen("https://6s890.lids.mit.edu/api/games/" + g["id"], timeout=30)
            d = json.loads(r.read())
            if "frames" not in d:
                raise ValueError("no frames")
            json.dump(d, open(path + ".tmp", "w")); os.replace(path + ".tmp", path)
            done += 1
            break
        except Exception as e:
            print("retry", g["id"], attempt, repr(e)[:120], flush=True)
            time.sleep(2 ** attempt)
    time.sleep(0.1)
    if done % 50 == 0 and done:
        print("done", done, flush=True)
print("finished", done, flush=True)
