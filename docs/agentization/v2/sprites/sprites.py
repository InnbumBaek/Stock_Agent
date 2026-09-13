# -*- coding: utf-8 -*-
"""픽셀 스프라이트 생성기 — 문자 그리드를 PNG 로 굽는다 (nearest-neighbour 확대)."""
import os, json
from PIL import Image

OUT = os.path.dirname(os.path.abspath(__file__))

def shade(hexc, f):
    r, g, b = int(hexc[0:2],16), int(hexc[2:4],16), int(hexc[4:6],16)
    if f >= 1: r,g,b = [min(255,int(v*f)) for v in (r,g,b)]
    else:      r,g,b = [max(0,int(v*f)) for v in (r,g,b)]
    return (r,g,b,255)

def bake(name, grid, pal, scale=18):
    h = len(grid); w = max(len(r) for r in grid)
    img = Image.new("RGBA", (w,h), (0,0,0,0))
    px = img.load()
    for y,row in enumerate(grid):
        for x,ch in enumerate(row):
            if ch in pal and pal[ch] is not None:
                px[x,y] = pal[ch]
    img = img.resize((w*scale, h*scale), Image.NEAREST)
    p = os.path.join(OUT, name + ".png")
    img.save(p)
    return p

# ── 로봇 에이전트 헤드 3종 ───────────────────────────────────────────
HEAD_TWO = [
 "................",
 ".......KK.......",
 "......KEEK......",
 ".......KK.......",
 "..KKKKKKKKKKKK..",
 ".KLLLLLLLLLLLLK.",
 ".KLBBBBBBBBBBLK.",
 ".KLBEEBBBBEEBLK.",
 ".KLBEEBBBBEEBLK.",
 ".KLBBBBBBBBBBLK.",
 ".KLBBKKKKKKBBLK.",
 ".KLBBBBBBBBBBLK.",
 ".KDDDDDDDDDDDDK.",
 "..KKKKKKKKKKKK..",
 "...KK......KK...",
 "................",
]
HEAD_VISOR = [
 "................",
 "......KKKK......",
 ".....KEEEEK.....",
 "......KKKK......",
 "..KKKKKKKKKKKK..",
 ".KLLLLLLLLLLLLK.",
 ".KLBBBBBBBBBBLK.",
 ".KLKEEEEEEEEKLK.",
 ".KLKEEEEEEEEKLK.",
 ".KLBBBBBBBBBBLK.",
 ".KLBKBKBKBKBBLK.",
 ".KLBBBBBBBBBBLK.",
 ".KDDDDDDDDDDDDK.",
 "..KKKKKKKKKKKK..",
 "...KK......KK...",
 "................",
]
HEAD_CYCLOPS = [
 "................",
 ".......KK.......",
 "......KEEK......",
 ".......KK.......",
 "..KKKKKKKKKKKK..",
 ".KLLLLLLLLLLLLK.",
 ".KLBBBBBBBBBBLK.",
 ".KLBBKEEEEKBBLK.",
 ".KLBBKEEEEKBBLK.",
 ".KLBBBKKKKBBBLK.",
 ".KLBBBBBBBBBBLK.",
 ".KLBKKBBBBKKBLK.",
 ".KDDDDDDDDDDDDK.",
 "..KKKKKKKKKKKK..",
 "...KK......KK...",
 "................",
]
HEAD_CROWN = [
 "..Y..YY..YY..Y..",
 "..YYYYYYYYYYYY..",
 "..YYYYYYYYYYYY..",
 "..KKKKKKKKKKKK..",
 "..KKKKKKKKKKKK..",
 ".KLLLLLLLLLLLLK.",
 ".KLBBBBBBBBBBLK.",
 ".KLBEEBBBBEEBLK.",
 ".KLBEEBBBBEEBLK.",
 ".KLBBBBBBBBBBLK.",
 ".KLBBKKKKKKBBLK.",
 ".KLBBBBBBBBBBLK.",
 ".KDDDDDDDDDDDDK.",
 "..KKKKKKKKKKKK..",
 "...KK......KK...",
 "................",
]

K = (10,13,22,255)
AGENTS = {
  "ag_equity":     ("4FC3F7", HEAD_TWO),
  "ag_quant":      ("9D7BFF", HEAD_VISOR),
  "ag_macro":      ("35D6ED", HEAD_TWO),
  "ag_exec":       ("FFB627", HEAD_VISOR),
  "ag_risk":       ("FF4D6D", HEAD_CYCLOPS),
  "ag_compliance": ("FF7847", HEAD_CYCLOPS),
  "ag_dataops":    ("3DFA7E", HEAD_TWO),
  "ag_chair":      ("FFD34E", HEAD_CROWN),
}
made = []
for name,(col,grid) in AGENTS.items():
    pal = {"K":K, "B":shade(col,1.0), "L":shade(col,1.35), "D":shade(col,0.62),
           "E":(232,246,255,255), "Y":shade("FFD34E",1.0), ".":None}
    made.append(bake(name, grid, pal))

# ── 오브젝트 스프라이트 ─────────────────────────────────────────────
PAPER = [
 "..KKKKKKKKKK....",
 "..KWWWWWWWWKK...",
 "..KWTTTTTTWWK...",
 "..KWWWWWWWWWK...",
 "..KWTTTTTTTWK...",
 "..KWTTTTTTTWK...",
 "..KWWWWWWWWWK...",
 "..KWTTTTTTTWK...",
 "..KWTTTTTWWWK...",
 "..KWWWWWWWWWK...",
 "..KWTTTTTTTWK...",
 "..KWTTTTWWWWK...",
 "..KWWWWWWWWWK...",
 "..KKKKKKKKKKK...",
 "................",
 "................",
]
DB = [
 "................",
 "...KKKKKKKKKK...",
 "..KLLLLLLLLLLK..",
 "..KBBBBBBBBBBK..",
 "..KKKKKKKKKKKK..",
 "..KLLLLLLLLLLK..",
 "..KBBBBBBBBBBK..",
 "..KKKKKKKKKKKK..",
 "..KLLLLLLLLLLK..",
 "..KBBBBBBBBBBK..",
 "..KKKKKKKKKKKK..",
 "..KLLLLLLLLLLK..",
 "..KBBBBBBBBBBK..",
 "...KKKKKKKKKK...",
 "................",
 "................",
]
GATE = [
 "KKKKKKKKKKKKKKKK",
 "KDDDDDDDDDDDDDDK",
 "KKKKKKKKKKKKKKKK",
 "K.B..B..B..B...K",
 "K.B..B..B..B...K",
 "K.B..B..B..B...K",
 "KKBKKBKKBKKBKKKK",
 "K.B..B..B..B...K",
 "K.B..B..B..B...K",
 "K.B..B..B..B...K",
 "KKBKKBKKBKKBKKKK",
 "K.B..B..B..B...K",
 "K.B..B..B..B...K",
 "KKKKKKKKKKKKKKKK",
 "................",
 "................",
]
WALL = [
 "KKKKKKKKKKKKKKKK",
 "KBBBBBBKBBBBBBBK",
 "KBBBBBBKBBBBBBBK",
 "KKKKKKKKKKKKKKKK",
 "KBBBKBBBBBBBKBBK",
 "KBBBKBBBBBBBKBBK",
 "KKKKKKKKKKKKKKKK",
 "KBBBBBBKBBBBBBBK",
 "KBBBBBBKBBBBBBBK",
 "KKKKKKKKKKKKKKKK",
 "KBBBKBBBBBBBKBBK",
 "KBBBKBBBBBBBKBBK",
 "KKKKKKKKKKKKKKKK",
 "KBBBBBBKBBBBBBBK",
 "KBBBBBBKBBBBBBBK",
 "KKKKKKKKKKKKKKKK",
]
CHECK = [
 "........",
 ".......B",
 "......BB",
 "B....BB.",
 "BB..BB..",
 ".BBBB...",
 "..BB....",
 "........",
]
CROSS = [
 "........",
 ".B....B.",
 ".BB..BB.",
 "..BBBB..",
 "...BB...",
 "..BBBB..",
 ".BB..BB.",
 ".B....B.",
]
ARROW = [
 "................",
 "................",
 "......B.........",
 "......BB........",
 "BBBBBBBBB.......",
 "BBBBBBBBBB......",
 "......BB........",
 "......B.........",
 "................",
 "................",
]
SPARK = [
 "....B...",
 "....B...",
 ".B..B..B",
 "..B.B.B.",
 "BBBBBBBB",
 "..B.B.B.",
 ".B..B..B",
 "....B...",
]
W = (232,236,245,255); T=(122,136,166,255)
made.append(bake("ob_paper", PAPER, {"K":K,"W":W,"T":T,".":None}))
made.append(bake("ob_db",    DB,    {"K":K,"B":shade("3DFA7E",0.85),"L":shade("3DFA7E",1.25),".":None}))
made.append(bake("ob_gate",  GATE,  {"K":K,"B":shade("FFB627",1.0),"D":shade("FFB627",0.6),".":None}))
made.append(bake("ob_wall",  WALL,  {"K":K,"B":shade("FFB627",0.55),".":None}, scale=10))
for nm,col in [("ok","3DFA7E"),("no","FF4D6D")]:
    g = CHECK if nm=="ok" else CROSS
    made.append(bake("ic_"+nm, g, {"B":shade(col,1.0),".":None}, scale=14))
for nm,col in [("cy","35D6ED"),("am","FFB627"),("gr","3DFA7E"),("mg","FF4D6D"),("pu","9D7BFF")]:
    made.append(bake("ar_"+nm, ARROW, {"B":shade(col,1.0),".":None}, scale=14))
made.append(bake("ic_spark", SPARK, {"B":shade("FFD34E",1.0),".":None}, scale=14))

CLOCK = [
 "................",
 ".....KKKKKK.....",
 "...KKWWWWWWKK...",
 "..KWWWWWWWWWWK..",
 ".KWWWWWKWWWWWWK.",
 ".KWWWWWKWWWWWWK.",
 "KWWWWWWKWWWWWWWK",
 "KWWWWWWKKKKWWWWK",
 "KWWWWWWWWWWWWWWK",
 "KWWWWWWWWWWWWWWK",
 ".KWWWWWWWWWWWWK.",
 ".KWWWWWWWWWWWWK.",
 "..KWWWWWWWWWWK..",
 "...KKWWWWWWKK...",
 ".....KKKKKK.....",
 "................",
]
BARS = [
 "................",
 "................",
 "..........BB....",
 "..........BB....",
 "......BB..BB....",
 "......BB..BB....",
 "..BB..BB..BB....",
 "..BB..BB..BB..BB",
 "..BB..BB..BB..BB",
 "..BB..BB..BB..BB",
 "KKKKKKKKKKKKKKKK",
 "................",
 "................",
 "................",
 "................",
 "................",
]
made.append(bake("ic_clock", CLOCK, {"K":K,"W":shade("35D6ED",1.0),".":None}, scale=14))
made.append(bake("ic_bars",  BARS,  {"K":shade("7A88A6",1.0),"B":shade("3DFA7E",1.0),".":None}, scale=14))

print("\n".join(os.path.basename(m) for m in made))
print("TOTAL", len(made))
