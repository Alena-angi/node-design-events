"""Put a real Aisance 1.6 screen into the AI-generated hands photo (green screen).
python3 -I compose_gen.py gen/gen-01.png assets/money.jpg out/gen-01-screen.png
"""
import sys, cv2, numpy as np
from PIL import Image, ImageDraw

photo_p, screen_p, out_p = sys.argv[1:4]
OUT_W, OUT_H = 1080, 1350

ph = cv2.imread(photo_p)
S = OUT_W / ph.shape[1]
ph = cv2.resize(ph, (OUT_W, OUT_H), interpolation=cv2.INTER_CUBIC)
b, g, r = [ph[:, :, i].astype(float) for i in range(3)]

# green-screen matte
greenness = g - np.maximum(r, b)
m = ((greenness > 80) & (g > 150)).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(m)
m = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]))
ys, xs = np.where(m)

# screen quad: fit straight edges of the matte
def fit(pts):
    # robust line fit: drop points pulled away by fingers / rounded corners
    p = np.array(pts, float)
    for _ in range(6):
        a, c = np.polyfit(p[:, 0], p[:, 1], 1)
        res = np.abs(p[:, 1] - (a * p[:, 0] + c))
        keep = res <= max(1.5, np.median(res) * 2.5)
        if keep.all() or keep.sum() < 8: break
        p = p[keep]
    return np.polyfit(p[:, 0], p[:, 1], 1)
y0, y1 = ys.min(), ys.max(); x0, x1 = xs.min(), xs.max(); h, w = y1 - y0, x1 - x0
mu = m.astype(np.uint8)
left = [(y, np.where(mu[y])[0].min()) for y in range(int(y0 + .12 * h), int(y0 + .88 * h)) if mu[y].any()]
right = [(y, np.where(mu[y])[0].max()) for y in range(int(y0 + .12 * h), int(y0 + .88 * h)) if mu[y].any()]
top = [(x, np.where(mu[:, x])[0].min()) for x in range(int(x0 + .22 * w), int(x0 + .78 * w)) if mu[:, x].any()]
bot = [(x, np.where(mu[:, x])[0].max()) for x in range(int(x0 + .22 * w), int(x0 + .78 * w)) if mu[:, x].any()]
Lf, Rf, Tf, Bf = fit(left), fit(right), fit(top), fit(bot)
def inter(xl, yl):
    a1, c1 = xl; a2, c2 = yl; y = (a2 * c1 + c2) / (1 - a1 * a2); return (a1 * y + c1, y)
quad = np.float32([inter(Lf, Tf), inter(Rf, Tf), inter(Rf, Bf), inter(Lf, Bf)])

# soft alpha for the screen area (keeps finger, island, bezel from the photo)
soft = np.clip((greenness - 25) / 70, 0, 1)
soft[~cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)] = 0

# our screen with rounded corners, warped
scr = Image.open(screen_p).convert('RGB'); sw, sh = scr.size
# clean status bar (9:41, full battery, no mute icon) — screenshots are 921 wide
import os
from PIL import ImageFont
k = sw / 921; dd = ImageDraw.Draw(scr)
dd.rectangle([0, 0, int(640 * k), int(115 * k)], fill=(0, 0, 0)); dd.rectangle([int(765 * k), 0, sw, int(115 * k)], fill=(0, 0, 0))
fnt = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fonts', 'Manrope-Bold.ttf'), int(38 * k))
dd.text((int(157 * k), int(68 * k)), '9:41', font=fnt, fill=(255, 255, 255), anchor='mm')
bx, by, bw, bh = int(772 * k), int(53 * k), int(56 * k), int(28 * k)
dd.rounded_rectangle([bx, by, bx + bw, by + bh], radius=int(8 * k), outline=(150, 150, 150), width=max(2, int(3 * k)))
dd.rounded_rectangle([bx + int(5 * k), by + int(5 * k), bx + bw - int(5 * k), by + bh - int(5 * k)], radius=int(4 * k), fill=(255, 255, 255))
smask = Image.new('L', (sw, sh), 0)
ImageDraw.Draw(smask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=int(sw * .13), fill=255)
rgba = np.dstack([cv2.cvtColor(np.array(scr), cv2.COLOR_RGB2BGR), np.array(smask)])
M = cv2.getPerspectiveTransform(np.float32([(0, 0), (sw, 0), (sw, sh), (0, sh)]), quad)
wp = cv2.warpPerspective(rgba, M, (OUT_W, OUT_H), flags=cv2.INTER_AREA, borderValue=(0, 0, 0, 0))
wa = wp[:, :, 3:4] / 255.0
screen = wp[:, :, :3] * wa                                   # black where our rounded corner ends

# despill: remove green cast on fingers and bezel edges near the screen
band = cv2.dilate(m.astype(np.uint8), np.ones((45, 45), np.uint8)).astype(bool)
g2 = np.where(band, np.minimum(g, (r + b) / 2 + 6), g)
ph2 = np.dstack([b, g2, r])

a = soft[..., None]
out = ph2 * (1 - a) + screen * a
# faint glass reflection over the screen
yy, xx = np.mgrid[0:OUT_H, 0:OUT_W].astype(float)
refl = np.clip(1 - (xx - quad[0][0]) / 380 - (yy - quad[0][1]) / 1000, 0, 1) * soft * 18
out = np.clip(out + refl[..., None], 0, 255).astype(np.uint8)
cv2.imwrite(out_p, out)
print('quad', quad.round(1).tolist())
