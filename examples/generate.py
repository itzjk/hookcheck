import math
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT, FPS, SECONDS = 270, 480, 24, 6


def scene(time_s, delayed):
    image = Image.new("RGB", (WIDTH, HEIGHT), "#eff0e8")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 368, 270, 480), fill="#bba385")
    draw.text((18, 24), "A VERY EXPENSIVE COFFEE", fill="#1d2933")
    active = not delayed or time_s >= 3
    if not active:
        draw.rounded_rectangle((80, 200, 188, 370), radius=28, fill="#355c7d")
        draw.ellipse((88, 100, 182, 202), fill="#dda37f")
        draw.ellipse((110, 144, 116, 152), fill="#1d2933")
        draw.ellipse((153, 144, 159, 152), fill="#1d2933")
        draw.line((120, 178, 148, 178), fill="#1d2933", width=3)
        draw.rounded_rectangle((23, 220, 247, 260), radius=10, fill="white")
        draw.text((45, 235), "LET ME EXPLAIN...", fill="#1d2933")
        draw.rectangle((140, 310, 240, 370), fill="#1d2933")
        draw.rectangle((150, 318, 230, 362), fill="#a8d8d0")
        draw.rectangle((20, 325, 60, 368), fill="#e9b949")
    else:
        phase = (time_s - 3 if delayed else time_s) % 2
        draw.text((18, 60), "COFFEE + LAPTOP =", fill="#1d2933")
        draw.text((18, 78), "OH NO.", fill="#a84435")
        draw.rounded_rectangle((18, 276, 252, 430), radius=12, fill="#1d2933")
        draw.rectangle((31, 288, 239, 360), fill="#a8d8d0")
        for row in range(3):
            for col in range(8):
                x, y = 35 + col * 25, 374 + row * 13
                draw.rectangle((x, y, x + 17, y + 7), fill="#6d7a83")
        draw.polygon([(132, 110), (219, 146), (184, 210), (103, 175)], fill="#e9b949", outline="#1d2933")
        draw.ellipse((99, 125, 143, 181), fill="#40291e")
        draw.ellipse((199, 148, 237, 187), outline="#e9b949", width=8)
        for index in range(24):
            y = 170 + ((phase * 380 + index * 17) % 250)
            x = 126 + math.sin(index * 2.3 + phase * 8) * (18 + (y - 170) / 4)
            radius = 5 + index % 9
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="#6b3d24")
        draw.text((24, 448), "SYNTHETIC HOOK FIXTURE", fill="#1d2933")
    return image


def generate():
    preview = []
    for delayed, name in ((True, "delayed-action"), (False, "action-first")):
        with tempfile.TemporaryFile() as pixels:
            for frame in range(FPS * SECONDS):
                pixels.write(scene(frame / FPS, delayed).tobytes())
            pixels.seek(0)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24",
                            "-video_size", f"{WIDTH}x{HEIGHT}", "-framerate", str(FPS), "-i", "pipe:0",
                            "-f", "lavfi", "-i", f"sine=frequency=440:duration={SECONDS}", "-t", str(SECONDS),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart",
                            str(ROOT / f"{name}.mp4")], stdin=pixels, check=True, timeout=60)
    for frame in range(SECONDS * 8):
        pair = Image.new("RGB", (WIDTH * 2, HEIGHT + 30), "#10131a")
        pair.paste(scene(frame / 8, True), (0, 30))
        pair.paste(scene(frame / 8, False), (WIDTH, 30))
        draw = ImageDraw.Draw(pair)
        draw.text((12, 10), "DELAYED ACTION", fill="white")
        draw.text((WIDTH + 12, 10), "ACTION FIRST", fill="white")
        preview.append(pair)
    preview[0].save(ROOT / "comparison.gif", save_all=True, append_images=preview[1:], duration=125, loop=0)


if __name__ == "__main__":
    generate()
