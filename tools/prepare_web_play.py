"""Prepare the official static website and the published browser game."""
import argparse
import json
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

p = argparse.ArgumentParser()
p.add_argument("archive")
p.add_argument("tag")
p.add_argument("output")
a = p.parse_args()
if not re.fullmatch(r"v\d+\.\d+\.\d+", a.tag):
    raise SystemExit("Invalid release version")
out = Path(a.output)
if out.exists():
    raise SystemExit("Output must not exist")
shutil.copytree("docs", out)
game = out / "juego"
game.mkdir()
with zipfile.ZipFile(a.archive) as z:
    files = {}
    total = 0
    for i in z.infolist():
        if i.is_dir():
            continue
        name = PurePosixPath(i.filename)
        if name.is_absolute() or ".." in name.parts or "\\" in i.filename or stat.S_ISLNK(i.external_attr >> 16):
            raise SystemExit("Unsafe path: " + i.filename)
        if str(name) in files:
            raise SystemExit("Duplicate path: " + i.filename)
        files[str(name)] = i
        total += i.file_size
    if total > 850_000_000:
        raise SystemExit("Game too large for GitHub Pages")
    if "index.html" not in files or not any(n.startswith("assets/") for n in files):
        raise SystemExit("Expected a complete web game with index.html and assets/ at the ZIP root")
    if z.testzip() is not None:
        raise SystemExit("Corrupt game ZIP")
    for name, i in files.items():
        target = game / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with z.open(i) as src, target.open("wb") as dest:
            shutil.copyfileobj(src, dest)
# Keep the original runtime and relative asset paths intact. No service worker:
# loading a newer release should not be blocked by old offline assets.
html = game / "index.html"
page = html.read_text(encoding="utf-8")
meta = '<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
icon = game / "assets" / "native-icons"
candidates = [icon / "mipmap-xxxhdpi" / "newen_launcher.png", icon / "newen.png"]
for item in candidates:
    if item.is_file():
        shutil.copy2(item, game / "apple-touch-icon.png")
        meta += '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n'
        break
if "</head>" in page:
    html.write_text(page.replace("</head>", meta + "</head>", 1), encoding="utf-8")
(game / "version.json").write_text(json.dumps({"version": a.tag, "platform": "web"}) + "\n", encoding="utf-8")
(out / ".nojekyll").touch()
size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
if size > 950_000_000:
    raise SystemExit("Website exceeds safe GitHub Pages size limit")
print("Website ready:", a.tag, len(files), "game files,", size, "bytes")
