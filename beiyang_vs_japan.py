#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
互動終端動畫：甲午戰爭海戰模擬（北洋水師 vs 日本海軍）
改良：
- 使用箭頭（→, ←）作為砲彈
- 船顯示為俯視（寬度 3 字元）
- 在 Windows 下支援簡單鍵盤互動：按 1-4 發射對應北洋艦
"""
import os
import sys
import time
import random

CLEAR_CMD = 'cls' if os.name == 'nt' else 'clear'

WIDTH = 72
HEIGHT = 14

try:
    import msvcrt
    HAS_MS = True
except Exception:
    HAS_MS = False

def clear():
    os.system(CLEAR_CMD)

def draw_glyph(sea, x, y, glyph):
    # place a multi-char glyph centered at x (glyph length assumed odd)
    half = len(glyph) // 2
    for i, ch in enumerate(glyph):
        tx = x - half + i
        if 0 <= y < HEIGHT and 0 <= tx < WIDTH:
            sea[y][tx] = ch

def render(frame, beiyang, japan, messages):
    clear()
    sea = [[' '] * WIDTH for _ in range(HEIGHT)]

    # horizon (decorative)
    for x in range(WIDTH):
        sea[1][x] = '~'

    # draw Beiyang fleet (left side) with top-down glyphs
    for i, pos in enumerate(beiyang):
        x, y, alive = pos
        glyph = '<B>' if alive else ' X '
        draw_glyph(sea, x, y, glyph)

    # draw Japanese fleet (right side)
    for i, pos in enumerate(japan):
        x, y, alive = pos
        glyph = '<J>' if alive else ' X '
        draw_glyph(sea, x, y, glyph)

    # draw projectiles
    for s in frame['shots']:
        sx, sy, d = s['x'], s['y'], s['dir']
        ch = '→' if d > 0 else '←'
        if 0 <= sy < HEIGHT and 0 <= sx < WIDTH:
            sea[sy][sx] = ch

    # render lines
    for row in sea:
        print(''.join(row))

    # messages
    print('-' * WIDTH)
    for m in messages:
        print(m)
    print('\n互動提示：按 1-4 發射北洋對應艦；按 q 結束（若支援鍵盤）')

def simulate():
    # let user choose formations for each side
    formations = ['line_ahead', 'line_abreast', 'echelon_right', 'echelon_left', 'wedge']
    print('可選隊形：', ', '.join(formations))
    b_form = input('請選擇北洋水師隊形（預設 line_ahead）: ').strip() or 'line_ahead'
    j_form = input('請選擇日本海軍隊形（預設 line_ahead）: ').strip() or 'line_ahead'

    def arrange_formation(side, formation, n, base_x):
        # returns list of [x,y,alive]
        res = []
        mid = HEIGHT // 2
        if formation == 'line_ahead':
            # column: same x, spread vertically
            for i in range(n):
                res.append([base_x, mid - (n-1) + i*2, True])
        elif formation == 'line_abreast':
            # line abreast: same y, spread horizontally
            y = mid
            startx = base_x - (n//2)*4
            for i in range(n):
                res.append([startx + i*4, y, True])
        elif formation == 'echelon_right':
            # diagonal down-right (for left side) or up-left (for right side)
            for i in range(n):
                res.append([base_x + i*3, mid - i*1 + (0 if side=='left' else 0), True])
        elif formation == 'echelon_left':
            for i in range(n):
                res.append([base_x - i*3, mid + i*1, True])
        elif formation == 'wedge':
            # V shape pointing towards enemy
            for i in range(n):
                offset = (i - n//2)
                res.append([base_x + abs(offset)*2 * (1 if side=='right' else -1), mid + i - n//2, True])
        else:
            # fallback to line_ahead
            for i in range(n):
                res.append([base_x, mid - (n-1) + i*2, True])
        # clamp y to valid range
        for r in res:
            if r[1] < 2: r[1] = 2
            if r[1] >= HEIGHT-1: r[1] = HEIGHT-2
            if r[0] < 1: r[0] = 1
            if r[0] >= WIDTH-1: r[0] = WIDTH-2
        return res

    # number of ships per fleet
    n_beiyang = 4
    n_japan = 4
    beiyang = arrange_formation('left', b_form if b_form in formations else 'line_ahead', n_beiyang, 6)
    japan = arrange_formation('right', j_form if j_form in formations else 'line_ahead', n_japan, WIDTH-7)

    frame = {'shots': []}
    messages = ["甲午戰爭海戰模擬：北洋水師 (B) vs 日本海軍 (J) - 互動版"]
    step = 0
    speed = 0.18

    try:
        while True:
            # handle keyboard input (non-blocking)
            if HAS_MS and msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ('q', 'Q'):
                    messages.insert(0, '玩家要求終止模擬')
                    break
                if ch in ('1','2','3','4'):
                    idx = int(ch)-1
                    if 0 <= idx < len(beiyang) and beiyang[idx][2]:
                        sx = beiyang[idx][0] + 2
                        sy = beiyang[idx][1]
                        frame['shots'].append({'x': sx, 'y': sy, 'dir': 1, 'owner': 'B'})
                        messages.insert(0, f'玩家：北洋第 {idx+1} 艦開火！')

            # AI random firing for both sides
            for i, ship in enumerate(beiyang):
                if ship[2] and random.random() < 0.12:
                    frame['shots'].append({'x': ship[0]+2, 'y': ship[1], 'dir': 1, 'owner': 'B'})

            for i, ship in enumerate(japan):
                if ship[2] and random.random() < 0.18:
                    frame['shots'].append({'x': ship[0]-2, 'y': ship[1], 'dir': -1, 'owner': 'J'})

            # move shots and resolve hits
            new_shots = []
            for s in frame['shots']:
                s['x'] += s['dir']
                # check collisions
                hit = False
                if s['owner'] == 'B':
                    for j, es in enumerate(japan):
                        if es[2] and abs(es[1]-s['y']) <= 0 and abs(es[0]-s['x']) <= 1:
                            es[2] = False
                            messages.insert(0, f"北洋命中日本艦第 {j+1} 艦！")
                            hit = True
                            break
                else:
                    for j, es in enumerate(beiyang):
                        if es[2] and abs(es[1]-s['y']) <= 0 and abs(es[0]-s['x']) <= 1:
                            es[2] = False
                            messages.insert(0, f"日本命中北洋艦第 {j+1} 艦！")
                            hit = True
                            break

                if not hit and 0 < s['x'] < WIDTH-1:
                    new_shots.append(s)

            frame['shots'] = new_shots

            # small approach movement
            for s in beiyang:
                if s[2] and s[0] < WIDTH//2 - 8:
                    s[0] += 1
            for s in japan:
                if s[2] and s[0] > WIDTH//2 + 8:
                    s[0] -= 1

            # count alive
            b_alive = sum(1 for s in beiyang if s[2])
            j_alive = sum(1 for s in japan if s[2])

            # status message
            messages.insert(0, f"步 {step} | 北洋艦: {b_alive} | 日本艦: {j_alive}")
            if len(messages) > 6:
                messages = messages[:6]

            render(frame, beiyang, japan, messages)

            if b_alive == 0 or j_alive == 0 or step > 200:
                break

            step += 1
            time.sleep(speed)

        # final summary
        if b_alive > j_alive:
            print('\n模擬結果：北洋水師勝利（模擬）')
        elif j_alive > b_alive:
            print('\n模擬結果：日本海軍勝利（模擬）')
        else:
            print('\n模擬結果：平手（模擬）')

    except KeyboardInterrupt:
        print('\n模擬中止。')

if __name__ == '__main__':
    simulate()
