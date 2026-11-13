"""Insert a real Aisance screen into the layered hand mockup (PSD layers exported as PNG).
python3 -I compose_phone.py <screen.webp|png> <out.png>
Output: 3000x2000 RGBA (hand + phone + screen + FX), transparent background.
"""
import sys, os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(HERE, n)
FONTS = os.path.join(HERE, '..', '..', 'fonts')
screen_p, out_p = sys.argv[1:3]
W, H = 3000, 2000

def place(img, xy):
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0)); c.paste(img, xy); return c

# ---- clean status bar: 9:41, full battery, no mute icon ----
scr = Image.open(screen_p).convert('RGB')
sw, sh = scr.size
d = ImageDraw.Draw(scr)
k = sw / 921
d.rectangle([0, 0, int(640 * k), int(115 * k)], fill=(0, 0, 0))          # time + mute icon area
d.rectangle([int(765 * k), 0, sw, int(115 * k)], fill=(0, 0, 0))         # battery area
font = ImageFont.truetype(os.path.join(FONTS, 'Manrope-Bold.ttf'), int(38 * k))
d.text((int(157 * k), int(68 * k)), '9:41', font=font, fill=(255, 255, 255), anchor='mm')
bx, by, bw, bh = int(772 * k), int(53 * k), int(56 * k), int(28 * k)
d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=int(8 * k), outline=(150, 150, 150), width=max(2, int(3 * k)))
d.rounded_rectangle([bx + int(5 * k), by + int(5 * k), bx + bw - int(5 * k), by + bh - int(5 * k)], radius=int(4 * k), fill=(255, 255, 255))
d.rounded_rectangle([bx + bw + int(3 * k), by + int(9 * k), bx + bw + int(7 * k), by + bh - int(9 * k)], radius=2, fill=(150, 150, 150))

# ---- warp into the smart-object quad (from PSD 'Trnf') ----
quad = np.float32([(967.94, 221.94), (1678.69, 31.53), (2086.24, 1552.20), (1375.49, 1742.61)])
src = np.float32([(0, 0), (sw, 0), (sw, sh), (0, sh)])
M = cv2.getPerspectiveTransform(src, quad)
arr = cv2.warpPerspective(np.array(scr), M, (W, H), flags=cv2.INTER_CUBIC)
mask_layer = place(Image.open(F('screen-mask.png')), (968, 31))
screen_alpha = np.array(mask_layer)[:, :, 3]
screen = Image.fromarray(np.dstack([arr, screen_alpha]))

base = place(Image.open(F('Base.png')), (408, 38))
out = Image.alpha_composite(base, screen)

# ---- FX: shadows (multiply), highlights (screen), only where the phone is ----
o = np.array(out).astype(float) / 255
for name, mode in (('fx-shadows.png', 'multiply'), ('fx-highlights.png', 'screen')):
    fx = np.array(place(Image.open(F(name)), (972, 38))).astype(float) / 255
    a = fx[:, :, 3:4]; c = fx[:, :, :3]
    blended = o[:, :, :3] * c if mode == 'multiply' else 1 - (1 - o[:, :, :3]) * (1 - c)
    o[:, :, :3] = o[:, :, :3] * (1 - a) + blended * a
Image.fromarray((o * 255).astype(np.uint8)).save(out_p)
print('saved', out_p)
