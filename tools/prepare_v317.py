"""Overlay the full web game on the existing native packaging project."""
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

def version(tag):
    v = tag.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        raise SystemExit("Use a tag such as v317.18.1")
    return v

if sys.argv[1] == "--android":
    v = version(sys.argv[2])
    major, minor, patch = map(int, v.split("."))
    code = major * 1000000 + minor * 1000 + patch
    if minor >= 1000 or patch >= 1000 or code > 2100000000:
        raise SystemExit("Invalid Android versionCode")
    gradle = Path("android/app/build.gradle")
    if not gradle.exists():
        gradle = Path("android/app/build.gradle.kts")
    s = gradle.read_text(encoding="utf-8")
    old = re.search(r"\bversionCode\s*(?:=\s*)?(\d+)", s)
    if not old:
        raise SystemExit("Cannot identify native Android versionCode")
    code = max(code, int(old.group(1)) + 1)
    s = re.sub(r"(\bversionCode\s*(?:=\s*)?)\d+", lambda m: m[1] + str(code), s, count=1)
    s, n = re.subn(r"(\bversionName\s*(?:=\s*)?)[\"'][^\"']*[\"']", lambda m: m[1] + '"' + v + '"', s, count=1)
    if n != 1:
        raise SystemExit("Cannot identify native Android versionName")
    gradle.write_text(s, encoding="utf-8")
    print("Android:", v, code)
    sys.exit(0)

base, web, tag = sys.argv[1:]
v = version(tag)
project = Path("project")
project.mkdir()
with zipfile.ZipFile(base) as z:
    z.extractall(project)
if not (project / "package.json").is_file():
    raise SystemExit("Base project layout differs from V316 workflow; inspect archive")
stage = Path("updated_web")
with zipfile.ZipFile(web) as z:
    z.extractall(stage)
required = ["index.html", "assets/newen31718_niebla.js", "assets/newen308_cacu.js", "assets/newen323_cinema.js"]
for f in required:
    if not (stage / f).is_file():
        raise SystemExit("Missing required updated web file: " + f)
pkgfile = project / "package.json"
pkg = json.loads(pkgfile.read_text(encoding="utf-8"))
pkg["version"] = v
pkg["repository"] = {"type": "git", "url": "https://github.com/zulguin/newenaraucania.git"}
pkg.setdefault("build", {})["publish"] = [{"provider":"github","owner":"zulguin","repo":"newenaraucania","channel":"latest"}]
# Keep the existing Electron entry and add a native updater for public betas.
tools_dir = Path(__file__).resolve().parent
main = pkg.get("main", "index.js")
if not (project / main).is_file():
    raise SystemExit("Cannot identify original Electron entry: " + main)
(project / "newen-original-main.json").write_text(json.dumps({"main": main}), encoding="utf-8")
shutil.copy2(tools_dir / "newen_windows_updater.cjs", project / "newen_windows_updater.cjs")
pkg["main"] = "newen_windows_updater.cjs"
deps = pkg.setdefault("dependencies", {})
deps.setdefault("electron-updater", "^6.3.9")
core = deps.get("@capacitor/core") or pkg.get("devDependencies", {}).get("@capacitor/core", "")
cap_major = re.search(r"\d+", core)
if cap_major:
    deps.setdefault("@capacitor/browser", "^" + cap_major.group() + ".0.0")
# If the native package restricts its file list, explicitly include the new entry.
files = pkg["build"].get("files")
if isinstance(files, str):
    files = [files]
if isinstance(files, list):
    files += ["newen_windows_updater.cjs", "newen-original-main.json"]
    pkg["build"]["files"] = files
pkgfile.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
targets = set()
for cfg in project.glob("capacitor.config.*"):
    if cfg.suffix == ".json":
        d = json.loads(cfg.read_text(encoding="utf-8")).get("webDir")
    else:
        m = re.search(r"\bwebDir\s*:\s*[\"']([^\"']+)[\"']", cfg.read_text(encoding="utf-8"))
        d = m[1] if m else None
    if d:
        p = (project / d).resolve()
        if not p.is_relative_to(project.resolve()):
            raise SystemExit("Unsafe webDir")
        targets.add(p)
        break
if not targets:
    raise SystemExit("Capacitor webDir not found; inspect base configuration")
# Update the native project web directory and any existing game root used by Electron.
for p in project.rglob("index.html"):
    if not {"node_modules", "android", "dist", ".git"}.intersection(p.relative_to(project).parts) and (p.parent / "assets").is_dir():
        targets.add(p.parent.resolve())
for p in sorted(targets):
    p.mkdir(parents=True, exist_ok=True)
    shutil.copytree(stage, p, dirs_exist_ok=True)
    # Android uses an update notice and opens the APK in a browser, not silent installation.
    shutil.copy2(tools_dir / "newen_update_notice.js", p / "assets" / "newen_update_notice.js")
    html = p / "index.html"
    page = html.read_text(encoding="utf-8")
    hook = '<script src="assets/newen_update_notice.js" data-version="' + v + '"></script>'
    if "</body>" not in page:
        raise SystemExit("Cannot insert update notice: missing body")
    html.write_text(page.replace("</body>", hook + "\n</body>", 1), encoding="utf-8")
    for f in required:
        if not (p / f).is_file():
            raise SystemExit("Overlay verification failed: " + str(p / f))
    print("Updated web game:", p.relative_to(project.resolve()))
print("Native packaging version:", v)
