"""
Generate Windows .ico and .png files for LOG NEST
"""
import sys
import os
import struct
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import Qt, QBuffer, QIODevice

app = QApplication.instance() or QApplication(sys.argv)

base_dir = os.path.dirname(os.path.abspath(__file__))
# Check for source image in user_uploaded or existing app_icon.png
src_candidates = [
    r"C:\Users\HP 3\.gemini\antigravity-ide\brain\dec28c99-3a74-4b9f-9670-b9711f420ea5\.user_uploaded\media_1792353412619.png",
    os.path.join(base_dir, "app_icon.png"),
]

src_path = None
for c in src_candidates:
    if os.path.exists(c):
        src_path = c
        break

if not src_path:
    print("Source image not found.")
    sys.exit(1)

base_img = QImage(src_path)

# Find bounding box of visible content
min_x, max_x = base_img.width(), 0
min_y, max_y = base_img.height(), 0
for y in range(base_img.height()):
    for x in range(base_img.width()):
        if base_img.pixelColor(x, y).alpha() > 10:
            if x < min_x: min_x = x
            if x > max_x: max_x = x
            if y < min_y: min_y = y
            if y > max_y: max_y = y

crop_w = max_x - min_x + 1
crop_h = max_y - min_y + 1
cropped = base_img.copy(min_x, min_y, crop_w, crop_h)

dim = max(crop_w, crop_h)
square_img = QImage(dim, dim, QImage.Format.Format_ARGB32)
square_img.fill(Qt.transparent)

painter = QPainter(square_img)
painter.setRenderHint(QPainter.Antialiasing)
painter.setRenderHint(QPainter.SmoothPixmapTransform)
painter.drawImage((dim - crop_w) // 2, (dim - crop_h) // 2, cropped)
painter.end()

# High-res PNG (512x512)
png_512 = square_img.scaled(512, 512, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
png_512.save(os.path.join(base_dir, "app_icon.png"), "PNG")
print("Saved app_icon.png (512x512)")

# Multi-resolution ICO
sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
png_blobs = []
for s in sizes:
    scaled = square_img.scaled(s, s, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    scaled.save(buf, "PNG")
    png_blobs.append((s, buf.data().data()))

num_images = len(png_blobs)
ico_header = struct.pack("<HHH", 0, 1, num_images)
offset = 6 + 16 * num_images
ico_entries = bytearray()
ico_data = bytearray()

for s, blob in png_blobs:
    w_byte = 0 if s == 256 else s
    h_byte = 0 if s == 256 else s
    size_blob = len(blob)
    entry = struct.pack("<BBBBHHII", w_byte, h_byte, 0, 0, 1, 32, size_blob, offset + len(ico_data))
    ico_entries.extend(entry)
    ico_data.extend(blob)

with open(os.path.join(base_dir, "app_icon.ico"), "wb") as f:
    f.write(ico_header + ico_entries + ico_data)

print(f"Saved app_icon.ico with sizes: {sizes}")
