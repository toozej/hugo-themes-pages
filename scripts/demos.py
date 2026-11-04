#!/usr/bin/env python3
"""Validate the demo manifest, build example sites, and create the public index."""

import argparse
import html
import json
from pathlib import Path, PurePosixPath
import re
import shutil
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
    optional = {"build_script"}
    for theme in themes:
        if (not isinstance(theme, dict) or not required <= set(theme)
                or not set(theme) <= required | optional):
            raise ValueError("Each theme must contain the documented required and optional fields")
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
        for field in ("example_site", "build_script"):
            if field not in theme:
                continue
            path = PurePosixPath(theme[field])
            if path.is_absolute() or ".." in path.parts or "\\" in str(path):
                raise ValueError(f"{field} must stay inside the theme for {slug}")
            if field == "build_script" and path.suffix != ".py":
                raise ValueError(f"build_script must name a Python file for {slug}")
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
    theme_url = base_url.rstrip("/") + "/" + slug + "/"
    generated = destination
    if "build_script" in theme:
        script = (checkout / theme["build_script"]).resolve()
        if not script.is_relative_to(checkout) or not script.is_file():
            raise ValueError("Build script is missing or outside the theme checkout")
        # Keep the wrapper's guarded public-* output inside its example site.
        generated = source / "public-pages"
        command = [sys.executable, str(script), "--source", str(source),
                   "--destination", generated.name, "--base-url", theme_url, "--check"]
    else:
        command = ["hugo", "--source", str(source), "--themesDir", str(checkout.parent),
                   "--theme", theme["theme"], "--destination", str(destination),
                   "--baseURL", theme_url, "--environment", "production",
                   "--cleanDestinationDir", "--minify"]
    # Template failures can contain private source excerpts. Never echo raw Hugo
    # diagnostics into this public repository's logs or upload them as artifacts.
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"Hugo build failed for {slug}. Reproduce locally using README.md; "
                         "private template diagnostics are intentionally omitted.")
    if generated != destination:
        check_output(generated)
        if destination.is_symlink():
            raise ValueError("Publication directory must not be a symlink")
        shutil.rmtree(destination)
        shutil.copytree(generated, destination)
    check_output(destination)
    print(f"Built {slug} at {theme_url}")


def make_index(themes):
    output = ROOT / "_site"
    for theme in themes:
        check_output(output / theme["slug"])
    cards = "\n".join(
        f'<li><a class="theme-card" href="./{t["slug"]}/"><h2>{html.escape(t["name"])}</h2>'
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
li{margin:32px 0}a{color:inherit;text-underline-offset:.18em}
.theme-card{display:block;text-decoration:none;border:1px solid #b3afa2;padding:28px}
.theme-card:hover,.theme-card:focus-visible{border-color:currentColor;background:#ede9df}h2{margin:0;font:2rem Georgia,serif}
section{margin-top:44px;border-top:1px solid #b3afa2;padding-top:32px}section h2{font-size:1.7rem}
pre{overflow-x:auto;border:1px solid #b3afa2;padding:20px;font-size:.8rem;line-height:1.7}
code{font-family:ui-monospace,monospace}p code{font-size:.85em}
p{max-width:640px}footer{margin-top:60px;font-size:.8rem;color:#67675e}
@media(prefers-color-scheme:dark){:root{background:#22231f;color:#eeeade}.theme-card:hover,.theme-card:focus-visible{background:#30322b}footer{color:#b3afa2}}
</style></head><body><p class="eyebrow">Hugo themes</p>
<h1>Themes in development.</h1>
<p>Explore the example sites built with <a href="https://gohugo.io/">Hugo</a>.
These demos follow the latest development versions. Read Hugo's
<a href="https://gohugo.io/getting-started/usage/">usage documentation</a> and
<a href="https://gohugo.io/documentation/">full documentation</a>, or follow the
<a href="#local-use">local setup instructions</a> to try a theme with a public repository.</p>
<ul>""" + cards + """</ul>
<section id="local-use" aria-labelledby="local-use-heading">
<h2 id="local-use-heading">Try a public theme locally</h2>
<p><a href="https://gohugo.io/installation/">Install Hugo</a> and Git first.
Check the theme's README for its required Hugo version, whether it needs Hugo Extended,
and any additional setup. The commands below assume the theme provides an <code>exampleSite</code> directory.</p>
<p>Replace <code>OWNER</code> and <code>THEME_REPO</code> with the public GitHub repository's
owner and name. Keep the checkout directory named <code>THEME_REPO</code>:</p>
<pre><code>git clone --recurse-submodules https://github.com/OWNER/THEME_REPO.git THEME_REPO
cd THEME_REPO
hugo server --source exampleSite --themesDir ../.. --theme THEME_REPO</code></pre>
<p>Open the local address Hugo prints, usually <code>http://localhost:1313/</code>.
Edit the example site's content or configuration to experiment; Hugo refreshes the preview
as you save. Press <code>Ctrl+C</code> in the terminal to stop the server.</p>
<p>To use a theme in your own site, follow the
<a href="https://gohugo.io/getting-started/quick-start/">Hugo quick start</a>
and the theme's README for installation and configuration.</p>
</section>
<footer>Built with Hugo and published with GitHub Actions.</footer></body></html>
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
