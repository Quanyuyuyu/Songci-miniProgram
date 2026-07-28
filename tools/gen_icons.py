# -*- coding: utf-8 -*-
"""生成 tabBar 图标：81x81 透明底 PNG，单色线稿，灰/墨蓝 两态共 8 张。"""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "miniprogram", "images", "tabbar")
SIZE = 81
W = 3  # 线宽
NORMAL = (138, 131, 120, 255)   # 辅助灰 #8A8378
ACTIVE = (47, 74, 110, 255)     # 墨蓝 #2F4A6E


def canvas():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def icon_scroll(d, c):
    # 卷轴：圆角矩形 + 上下轴 + 两行字
    d.rounded_rectangle([16, 22, 65, 60], radius=6, outline=c, width=W)
    d.line([16, 30, 65, 30], fill=c, width=W)
    d.line([27, 40, 54, 40], fill=c, width=W)
    d.line([27, 49, 48, 49], fill=c, width=W)
    d.ellipse([11, 26, 21, 34], outline=c, width=W)
    d.ellipse([60, 26, 70, 34], outline=c, width=W)


def icon_brush(d, c):
    # 笔 + 方框（作业自检）
    d.rounded_rectangle([14, 14, 67, 67], radius=8, outline=c, width=W)
    d.line([26, 56, 52, 30], fill=c, width=W)
    d.line([52, 30, 58, 24], fill=c, width=W)
    d.line([58, 24, 62, 28], fill=c, width=W)
    d.line([58, 24, 54, 34], fill=c, width=W)
    d.line([24, 44, 31, 51], fill=c, width=W)
    d.line([31, 51, 44, 38], fill=c, width=W)


def icon_stack(d, c):
    # 三层叠块（档案）
    d.rounded_rectangle([20, 16, 61, 30], radius=4, outline=c, width=W)
    d.rounded_rectangle([16, 33, 65, 47], radius=4, outline=c, width=W)
    d.rounded_rectangle([12, 50, 69, 65], radius=4, outline=c, width=W)


def icon_seal(d, c):
    # 印章（资料）：方印 + 内纹
    d.rounded_rectangle([17, 17, 64, 64], radius=8, outline=c, width=W)
    d.line([40, 26, 40, 55], fill=c, width=W)
    d.line([29, 34, 52, 34], fill=c, width=W)
    d.line([29, 47, 52, 47], fill=c, width=W)
    d.arc([24, 24, 34, 34], 180, 360, fill=c, width=W)


ICONS = {"overview": icon_scroll, "homework": icon_brush,
         "archive": icon_stack, "library": icon_seal}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in ICONS.items():
        for suffix, color in (("", NORMAL), ("-active", ACTIVE)):
            img, d = canvas()
            fn(d, color)
            path = os.path.join(OUT, f"{name}{suffix}.png")
            img.save(path)
            print("saved", path)


if __name__ == "__main__":
    main()
