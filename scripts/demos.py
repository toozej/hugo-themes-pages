#!/usr/bin/env python3
"""Validate the demo manifest, build example sites, and create the public index."""

import argparse
import html
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def load_themes():
    themes = json.loads((ROOT / "themes.json").read_text())
    if not isinstance(themes, list) or not 1 <= len(themes) <= 256:
        raise ValueError("themes.json must contain between 1 and 256 themes")
    seen = set()
    required = {"slug", "name", "description", "repository", "ref", "example_site",
                "theme", "hugo_version", "ssh_key_secret"}
    for theme in themes:
        if not isinstance(theme, dict) or set(theme) != required:
            raise ValueError("Each theme must contain exactly the documented fields")
        if any(not isinstance(value, str) or not value or "\n" in value or "\r" in value
               for value in theme.values()):
            raise ValueError("Theme fields must be nonempty single-line strings")
        slug = theme["slug"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or slug in seen:
            raise ValueError("Theme slugs must be unique lowercase URL names")
        seen.add(slug)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", theme["repository"]):
            raise ValueError(f"Invalid repository for {slug}")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", theme["theme"]):
            raise ValueError(f"Invalid theme directory for {slug}")
        path = PurePosixPath(theme["example_site"])
        if path.is_absolute() or ".." in path.parts or "\\" in str(path):
            raise ValueError(f"example_site must stay inside the theme for {slug}")
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", theme["hugo_version"]):
            raise ValueError(f"Use an explicit Hugo version for {slug}")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", theme["ssh_key_secret"]):
            raise ValueError(f"Invalid SSH secret name for {slug}")
    return themes


def check_output(directory):
    if not (directory / "index.html").is_file():
        raise ValueError(f"Missing generated index.html in {directory.name}")
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("Publication directory must not contain symlinks")
        if any(part in {".git", ".github", "node_modules", "_themes"}
               for part in path.relative_to(directory).parts):
            raise ValueError("Source checkout found in publication directory")
        if path.suffix.lower() in {".pem", ".key"}:
            raise ValueError("Key file found in publication directory")


def build(themes, slug, base_url):
    theme = next((item for item in themes if item["slug"] == slug), None)
    if theme is None:
        raise ValueError("Unknown theme slug")
    url = urlsplit(base_url)
    if url.scheme not in {"http", "https"} or not url.netloc or url.query or url.fragment:
        raise ValueError("base-url must be an absolute HTTP(S) site URL")
    checkout = (ROOT / "_themes" / theme["theme"]).resolve()
    source = (checkout / theme["example_site"]).resolve()
    if not source.is_relative_to(checkout) or not source.is_dir():
        raise ValueError("Example site is missing or outside the theme checkout")
    destination = ROOT / "_site" / slug
    destination.mkdir(parents=True, exist_ok=True)
    command = ["hugo", "--source", str(source), "--themesDir", str(checkout.parent),
               "--theme", theme["theme"], "--destination", str(destination),
               "--baseURL", base_url.rstrip("/") + "/" + slug + "/",
               "--environment", "production", "--cleanDestinationDir", "--minify"]
    # Template failures can contain private source excerpts. Never echo raw Hugo
    # diagnostics into this public repository's logs or upload them as artifacts.
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"Hugo build failed for {slug}. Reproduce locally using README.md; "
                         "private template diagnostics are intentionally omitted.")
    check_output(destination)
    print(f"Built {slug} at {base_url.rstrip('/')}/{slug}/")


def make_index(themes):
    output = ROOT / "_site"
    for theme in themes:
        check_output(output / theme["slug"])
    cards = "\n".join(
        f'<li><a href="./{t["slug"]}/"><h2>{html.escape(t["name"])}</h2>'
        f'<p>{html.escape(t["description"])}</p><span>View demo →</span></a></li>'
        for t in themes
    )
    (output / "index.html").write_text("""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hugo theme demos</title><style>
:root{color-scheme:light dark;font:18px/1.6 system-ui,sans-serif;background:#f7f4ed;color:#252521}
body{max-width:900px;margin:8vh auto;padding:24px}h1{font:clamp(2.5rem,7vw,4rem)/1.1 Georgia,serif}
.eyebrow,span{font-size:.8rem;letter-spacing:.1em;text-transform:uppercase}ul{list-style:none;padding:0}
li{margin:32px 0}a{display:block;color:inherit;text-decoration:none;border:1px solid #b3afa2;padding:28px}
a:hover,a:focus-visible{border-color:currentColor;background:#ede9df}h2{margin:0;font:2rem Georgia,serif}
p{max-width:640px}footer{margin-top:60px;font-size:.8rem;color:#67675e}
@media(prefers-color-scheme:dark){:root{background:#22231f;color:#eeeade}a:hover,a:focus-visible{background:#30322b}footer{color:#b3afa2}}
</style></head><body><p class="eyebrow">Hugo themes</p>
<h1>Themes in development.</h1><p>Explore the example sites. These demos follow the latest development versions.</p>
<ul>""" + cards + """</ul><footer>Built with Hugo and published with GitHub Actions.</footer></body></html>
""")
    (output / ".nojekyll").touch()
    check_output(output)
    print(f"Assembled {len(themes)} theme demo(s)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("matrix")
    builder = commands.add_parser("build")
    builder.add_argument("slug")
    builder.add_argument("--base-url", required=True)
    commands.add_parser("index")
    args = parser.parse_args()
    try:
        themes = load_themes()
        if args.command == "matrix":
            print("themes=" + json.dumps(themes, separators=(",", ":")))
        elif args.command == "build":
            build(themes, args.slug, args.base_url)
        else:
            make_index(themes)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
