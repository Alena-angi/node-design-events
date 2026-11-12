"""1:1 draft of the reference: hands + phone body from the reference photo,
our real 1.6 screen warped into the phone, brand background instead of the sky.
DRAFT ONLY: hands come from a third-party reference photo, replace before publishing.

python3 -I aisance-instagram/hand-closeup/compose.py [screen.jpg] [out-name]
"""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(HERE, *p)
SCREEN = sys.argv[1] if len(sys.argv) > 1 else A('assets', 'money.jpg')
NAME = sys.argv[2] if len(sys.argv) > 2 else 'hand-1to1'
OUT_W, OUT_H = 1080, 1350

ref = cv2.imread(A('assets', 'reference.jpg'))            # 736x920, BGR
rh, rw = ref.shape[:2]
S = OUT_W / rw                                              # 1.4674

# ---------- 1. remove the reference captions (at reference resolution) ----------
b, g, r = [ref[:, :, i].astype(int) for i in range(3)]
L = (r + g + b) / 3
skin_r = (r - b > 12)
txt = np.zeros((rh, rw), np.uint8)
y0, y1 = 834, 870                                            # caption rows
Lu8 = L.astype(np.uint8)
bgL = cv2.medianBlur(Lu8, 21).astype(int)
grey = (np.abs(r - b) < 15)
cand = (L < bgL - 8) | (grey & (L < 200))
txt[y0:y1, 30:445] = cand[y0:y1, 30:445].astype(np.uint8) * 255
txt = cv2.dilate(txt, np.ones((3, 3), np.uint8), 2)
clean = cv2.inpaint(ref, txt, 6, cv2.INPAINT_TELEA)

# ---------- 2. masks (reference resolution), then upscale ----------
b, g, r = [clean[:, :, i].astype(int) for i in range(3)]
L = (r + g + b) / 3
sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
skin = (r - b > 12) & (L < 200)

quad_ref = np.array([(219.5, 267.5), (382, 250), (497.5, 644.5), (335.5, 668.5)], np.float32)
def poly(pts, grow=0):
    m = np.zeros((rh, rw), np.uint8); cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 255)
    if grow > 0: m = cv2.dilate(m, np.ones((grow, grow), np.uint8))
    if grow < 0: m = cv2.erode(m, np.ones((-grow, -grow), np.uint8))
    return m > 0
inq = poly(quad_ref, 3)
body = poly(quad_ref, 26)                                    # phone frame around the screen

def capsule(c0, c1, rad):
    m = np.zeros((rh, rw), np.uint8)
    cv2.line(m, tuple(map(int, c0)), tuple(map(int, c1)), 1, int(rad * 2))
    cv2.circle(m, tuple(map(int, c0)), int(rad), 1, -1); cv2.circle(m, tuple(map(int, c1)), int(rad), 1, -1)
    return m > 0
p1 = capsule((437, 312), (487, 308), 37)
p2 = capsule((251, 547), (327, 537), 38)

dark = np.clip((142 - L) / 25, 0, 1)                         # hands + bezel vs bright sky
keep = np.maximum(dark, skin.astype(float))
skyish = (b - r > 14) & (L > 140)
fr = body & ~inq & ~skyish & (L < 215)
keep[fr] = np.maximum(keep[fr], 1.0)
finger = np.zeros_like(inq); finger[495:, 365:] = True
keep[inq] = (skin & (L < 125) & finger)[inq].astype(float)   # only the finger stays over the screen
keep[p1 | p2] = 1.0
keep[:140] = 0                                               # "Mobile Adaptation" + corner mark
a = cv2.resize((keep * 255).astype(np.uint8), (OUT_W, OUT_H), interpolation=cv2.INTER_LINEAR)
a = cv2.GaussianBlur(a, (0, 0), 0.8)
up = cv2.resize(clean, (OUT_W, OUT_H), interpolation=cv2.INTER_CUBIC)
quad = quad_ref * S
pill_mask_up = cv2.resize(((p1 | p2) * 255).astype(np.uint8), (OUT_W, OUT_H)) > 127

# cool sky light on the hands -> slight teal grade so they sit in the brand background
teal = np.array([0x7F, 0x7A, 0x2A], float)                  # BGR of #2A7A7F
layer = up.astype(float) * 0.9 + teal * 0.1
layer = np.clip(layer, 0, 255).astype(np.uint8)

# ---------- 3. our screen, warped into the phone ----------
scr = Image.open(SCREEN).convert('RGB')
sw, sh = scr.size
d = ImageDraw.Draw(scr)
iw, ih, it = int(sw * .32), int(sh * .043), int(sh * .013)    # Dynamic Island
d.rounded_rectangle([(sw - iw) // 2, it, (sw + iw) // 2, it + ih], radius=ih // 2, fill=(0, 0, 0))
rad = int(sw * .14)
smask = Image.new('L', (sw, sh), 0)
ImageDraw.Draw(smask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=rad, fill=255)
scr_rgba = np.dstack([cv2.cvtColor(np.array(scr), cv2.COLOR_RGB2BGR), np.array(smask)])
M = cv2.getPerspectiveTransform(np.float32([(0, 0), (sw, 0), (sw, sh), (0, sh)]), quad)
warped = cv2.warpPerspective(scr_rgba, M, (OUT_W, OUT_H), flags=cv2.INTER_AREA if S < 1 else cv2.INTER_CUBIC)

# ---------- 4. brand background ----------
yy, xx = np.mgrid[0:OUT_H, 0:OUT_W].astype(float)
ang = np.deg2rad(165 - 90)
t = (xx * np.cos(ang) + yy * np.sin(ang)); t = (t - t.min()) / (t.max() - t.min())
c0, c1, c2 = [np.array(c, float) for c in [(0x3B, 0x3A, 0x10), (0x4F, 0x50, 0x17), (0x7F, 0x7A, 0x2A)]]
bg = np.where(t[..., None] < .5, c0 + (c1 - c0) * (t[..., None] / .5), c1 + (c2 - c1) * ((t[..., None] - .5) / .5))
light = np.exp(-(((xx - .70 * OUT_W) / 520) ** 2 + ((yy - .15 * OUT_H) / 420) ** 2)) * 20
bg = np.clip(bg + light[..., None], 0, 255)

# ---------- 5. composite ----------
out = bg.copy()
black = cv2.dilate((warped[:, :, 3] > 8).astype(np.uint8) * 255, np.ones((5, 5), np.uint8))
out[black > 0] = 0                                            # bezel under rounded corners
wa = warped[:, :, 3:4] / 255.0
out = out * (1 - wa) + warped[:, :, :3] * wa
# subtle glass reflection on the screen
refl = np.clip(1 - (xx - quad[0][0]) / 420 - (yy - quad[0][1]) / 900, 0, 1) * (black > 0) * 22
out = np.clip(out + refl[..., None], 0, 255)
ha = a[..., None] / 255.0
out = out * (1 - ha) + layer * ha
out = out.astype(np.uint8)

# hands-only transparent layer (for Figma)
hands = np.dstack([layer, a])

# ---------- 6. pill 1: our number instead of "56%" ----------
pil = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
cx, cy, rr = 487 * S, 309 * S, 23 * S
dr = ImageDraw.Draw(pil)
dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 255, 255))
font = ImageFont.truetype(A('..', 'fonts', 'Manrope-Bold.ttf'), int(15 * S))
dr.text((cx, cy), '64%', font=font, fill=(0x1B, 0x1E, 0x21), anchor='mm')

os.makedirs(A('out'), exist_ok=True)
pil.save(A('out', NAME + '.png'))
Image.fromarray(cv2.cvtColor(hands, cv2.COLOR_BGRA2RGBA)).save(A('out', NAME + '-hands-layer.png'))
print('saved', NAME)
