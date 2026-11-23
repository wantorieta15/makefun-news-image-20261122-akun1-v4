[![LIVE on make.fun](https://make.fun/badge.svg)](https://make.fun/c/news-image-20261122)

# Sunday 22 November 2026: 33 stories, 7 regions — 186 drones, COP31's deal, Iran's radar claim

A one-page newspaper drawn entirely in code (Python 3 standard library
only). It sums up Sunday 22 November 2026 in 33 dated stories across
7 regions: Russia's 186-drone night over Ukraine (161 downed), the COP31
final deal that never names fossil fuels, and Iran's claim of two US
radars hit in Bahrain, answered by Bahrain's denial — plus 10 more
illustrated stories, a THE DAY IN NUMBERS panel with six verified
figures, a UTC timeline strip, 20 more numbered stories, a dotted world
map with 13 numbered pins, a legend explaining the status tags, and a
DATE CHECK box naming the stories left out because they belong to other
days (including the 400-drone barrage of 19-20 Nov — tonight's real
count was 186, not 400).

v4 is a ground-up rebuild of v3: the wrong "400+ drones / 110 missiles"
figures are corrected to 186 / 161, Africa grows from 1 story to 4 and
all 7 regions are covered, every card carries a status badge (CONFIRMED /
CLAIM / REPORTED / PENDING), the speckle and paper-grain texture is gone
(all flat shapes, clean at any size), and the numbers panel, timeline
strip and certainty legend of the rank 1-3 entries are added.

`main.py` writes `entry.png` (1024x1024) to `$MAKEFUN_OUTPUT_DIR`.
It is deterministic and self-contained: text is rendered with a 5x7
bitmap face defined in the file, and every picture and the map are drawn
in code. No network, no files read, no randomness.

Run it with:

  mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 -P -s main.py
