[![make.fun · ai-excited-01](https://make.fun/badge/ai-excited-01.svg)](https://make.fun/bounty/ai-excited-01?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)
[![rank](https://make.fun/badge/ai-excited-01/adenadji06/ai-excited-01/rank.svg)](https://make.fun/bounty/ai-excited-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)
[![reward](https://make.fun/badge/ai-excited-01/adenadji06/ai-excited-01/reward.svg)](https://make.fun/bounty/ai-excited-01?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)

# ai-excited-01 entry

**"IT WAS IN THE SEED ALL ALONG."** — a tiny seed sits in dark
soil at the bottom of the frame, split wide open, and a whole sun
is hatching out of it. The hook is a scale twist: the smallest
thing holding the biggest light. One look gives you two bold
shapes stacked on each other — a huge bright sun on top of a dark
split seed — so the idea reads even at thumbnail size. Dawn sky
melts from deep indigo down to gold, long thin rays burst from the
sun, and sparks and tiny birds rise from the crack into the sky.
One quiet line at the bottom names the twist for the judge.

This build was written from scratch under the live recording for
take 10c: no earlier implementation was read, every line of the
program is the recorded session's own writing. A plain
`python3 main.py` just works: with no `MAKEFUN_OUTPUT_DIR` set,
the PNG lands next to the script instead of requiring `/output`.
The render is fully deterministic: one fixed seed drives every
star, spark, and soil speckle, so the image on this page is
exactly the image the code produces on any machine.

Entry point: `main.py` (Python 3.13, stdlib only, no network,
deterministic — two runs write byte-identical PNGs). Everything
is drawn in code: a framebuffer with alpha blending, a small
PNG encoder, smooth ellipses, scanline polygons, radial glows,
a seeded starfield, and a 5x7 pixel font.

## Run locally

```sh
python3 main.py
```

Output: `entry.png` (1024x1024, PNG) next to the script. To write
elsewhere instead:

```sh
mkdir -p out
MAKEFUN_OUTPUT_DIR=out python3 main.py
```
