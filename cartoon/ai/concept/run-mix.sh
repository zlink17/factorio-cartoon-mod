set -e
PY=/home/zlink17/workspace/factorio-cartoon-mod/.venv/bin/python
P="cartoon video game sprite of a rocket thruster engine machine, seen from above, top-down view, flat colors, cel shading, thick dark outlines, bold clean shapes, vivid high contrast colors: cream beige body panels, dark steel grey frame, bright copper orange pipes, blue hoses, glowing orange fire inside the open nozzle bell, plain grey background."
$PY -I concept.py guides gen 31,32 --tag m55 --init gen/a-13.png --denoise 0.55 --edges-file trait-a13.png --edges 0.6 --depth 0.5 --styles couleurs-b22.png --style 0.8 --cfg 2.5 --base-prompt "$P"
$PY -I concept.py guides gen 41,42 --tag m70 --init gen/a-13.png --denoise 0.7 --edges-file trait-a13.png --edges 0.7 --depth 0.5 --styles couleurs-b22.png --style 0.8 --cfg 2.5 --base-prompt "$P"
