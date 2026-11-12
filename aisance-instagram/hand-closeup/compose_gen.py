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
    p = np.array(pts, float); return np.polyfit(p[:, 0], p[:, 1], 1)
y0, y1 = ys.min(), ys.max(); x0, x1 = xs.min(), xs.max(); h, w = y1 - y0, x1 - x0
mu = m.astype(np.uint8)
left = [(y, np.where(mu[y])[0].min()) for y in range(int(y0 + .2 * h), int(y0 + .7 * h)) if mu[y].any()]
right = [(y, np.where(mu[y])[0].max()) for y in range(int(y0 + .15 * h), int(y0 + .65 * h)) if mu[y].any()]
top = [(x, np.where(mu[:, x])[0].min()) for x in range(int(x0 + .25 * w), int(x0 + .7 * w)) if mu[:, x].any()]
bot = [(x, np.where(mu[:, x])[0].max()) for x in range(int(x0 + .25 * w), int(x0 + .62 * w)) if mu[:, x].any()]
Lf, Rf, Tf, Bf = fit(left), fit(right), fit(top), fit(bot)
def inter(xl, yl):
    a1, c1 = xl; a2, c2 = yl; y = (a2 * c1 + c2) / (1 - a1 * a2); return (a1 * y + c1, y)
quad = np.float32([inter(Lf, Tf), inter(Rf, Tf), inter(Rf, Bf), inter(Lf, Bf)])

# soft alpha for the screen area (keeps finger, island, bezel from the photo)
soft = np.clip((greenness - 25) / 70, 0, 1)
soft[~cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)] = 0

# our screen with rounded corners, warped
scr = Image.open(screen_p).convert('RGB'); sw, sh = scr.size
smask = Image.new('L', (sw, sh), 0)
ImageDraw.Draw(smask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=int(sw * .13), fill=255)
rgba = np.dstack([cv2.cvtColor(np.array(scr), cv2.COLOR_RGB2BGR), np.array(smask)])
M = cv2.getPerspectiveTransform(np.float32([(0, 0), (sw, 0), (sw, sh), (0, sh)]), quad)
wp = cv2.warpPerspective(rgba, M, (OUT_W, OUT_H), flags=cv2.INTER_AREA, borderValue=(0, 0, 0, 0))
wa = wp[:, :, 3:4] / 255.0
screen = wp[:, :, :3] * wa                                   # black where our rounded corner ends

# despill: remove green cast on fingers and bezel edges near the screen
band = cv2.dilate(m.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
g2 = np.where(band, np.minimum(g, (r + b) / 2 + 12), g)
ph2 = np.dstack([b, g2, r])

a = soft[..., None]
out = ph2 * (1 - a) + screen * a
# faint glass reflection over the screen
yy, xx = np.mgrid[0:OUT_H, 0:OUT_W].astype(float)
refl = np.clip(1 - (xx - quad[0][0]) / 380 - (yy - quad[0][1]) / 1000, 0, 1) * soft * 18
out = np.clip(out + refl[..., None], 0, 255).astype(np.uint8)
cv2.imwrite(out_p, out)
print('quad', quad.round(1).tolist())
