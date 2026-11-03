# Hugo theme demos

Build Hugo themes' `exampleSite` directories from private repositories and publish the rendered demos together on GitHub Pages.

**Demo index:** https://toozej.github.io/hugo-themes-pages/

| Theme | Source | Demo |
| --- | --- | --- |
| Folio | `toozej/hugo-theme-folio` (private) | https://toozej.github.io/hugo-themes-pages/folio/ |

## How it works

[`themes.json`](themes.json) is the theme list. GitHub Actions checks out each theme at its configured branch, tag, or commit, installs its pinned Hugo Extended version, and builds its example site with `baseURL` set to `https://toozej.github.io/hugo-themes-pages/<slug>/`.

The builds run in parallel. A separate job collects only their generated `_site/<slug>/` directories, adds a demo index, and publishes one Pages artifact. Publication waits for every build to succeed; a failed theme build leaves the previous deployment intact.

Builds run on pushes to `main`, manually from **Actions → Build and deploy theme demos → Run workflow**, and hourly at minute 17 to pick up private theme changes. Scheduled runs may be delayed by GitHub. GitHub disables scheduled workflows in inactive public repositories after 60 days; push a change or re-enable the workflow in Actions if that happens. Pull requests validate only the public theme list and never check out private source or receive deploy keys.

## Initial setup

1. In this repository, set **Settings → Pages → Build and deployment → Source** to **GitHub Actions**.
2. Give each private theme a separate **read-only deploy key**. For Folio:

   ```sh
   ssh-keygen -t ed25519 -C 'hugo-themes-pages:folio' -f folio-demo -N ''
   ```

   Add `folio-demo.pub` in **toozej/hugo-theme-folio → Settings → Deploy keys → Add deploy key**. Leave **Allow write access** unchecked.

3. Add the contents of `folio-demo` as an Actions repository secret named **`FOLIO_DEPLOY_KEY`** in **this public repository → Settings → Secrets and variables → Actions**. Never commit either private keys or theme checkouts. Once configured, keep the original key in a secure credential store or remove the local copy.
4. Run the deployment workflow and open the demo URL above.

The public repository's default `GITHUB_TOKEN` cannot read an unrelated private repository. The deploy key supplies only that theme's Git read access; deployment uses the workflow's short-lived Pages token. No personal access token or write access to a private theme is needed.

## Add another theme

Create its read-only deploy key and Actions secret, then append an entry to `themes.json`:

```json
{
  "slug": "another-theme",
  "name": "Another theme",
  "description": "A short description for the demo index.",
  "repository": "toozej/hugo-theme-another",
  "ref": "main",
  "example_site": "exampleSite",
  "theme": "hugo-theme-another",
  "hugo_version": "0.158.0",
  "ssh_key_secret": "ANOTHER_THEME_DEPLOY_KEY"
}
```

| Field | Meaning |
| --- | --- |
| `slug` | Unique lowercase URL segment, such as `folio`. |
| `name`, `description` | Public text shown on the demo index. |
| `repository` | GitHub `owner/repository` to check out. |
| `ref` | Branch to follow, or tag/commit to pin. |
| `example_site` | Example-site directory relative to the theme root. |
| `theme` | Checkout directory and Hugo theme name; match the theme's configuration. |
| `hugo_version` | Exact Hugo Extended release used for this theme. |
| `ssh_key_secret` | Name of this repository's Actions secret containing the private deploy key. |

The example site must build directly with Hugo. If a future theme needs npm preprocessing, Hugo modules, submodules, or LFS, add those explicit setup steps before enabling it. Folio needs none of these.

## Local build

Requires Python 3.10+, Git, and the manifest's Hugo Extended release. Clone private themes using your existing GitHub SSH access:

```sh
git clone https://github.com/toozej/hugo-themes-pages.git
cd hugo-themes-pages
git clone --branch main git@github.com:toozej/hugo-theme-folio.git _themes/hugo-theme-folio
python3 scripts/demos.py matrix
python3 scripts/demos.py build folio --base-url https://toozej.github.io/hugo-themes-pages/
python3 scripts/demos.py index
```

Serve `_site` beneath `/hugo-themes-pages/` when checking the exact production paths. For a quick root-hosted local preview, rebuild with `--base-url http://localhost:8000/`, run `python3 scripts/demos.py index`, then `python3 -m http.server 8000 --directory _site`.

If CI reports a Hugo failure, run the equivalent Hugo command locally to see full diagnostics:

```sh
hugo --source _themes/hugo-theme-folio/exampleSite \
  --themesDir "$(pwd)/_themes" --theme hugo-theme-folio \
  --destination "$(pwd)/_site/folio" \
  --baseURL https://toozej.github.io/hugo-themes-pages/folio/ \
  --environment production --cleanDestinationDir --minify
```

## Source privacy

Theme Git history, Hugo templates, Markdown, and configuration stay in the private repositories and temporary runners. They are never copied into this public repository or uploaded as build artifacts. Raw Hugo failure diagnostics are suppressed because they can include private template excerpts. Only generated site files are uploaded, with one-day artifact retention. Actions are pinned to commit SHAs and checkout credentials are not persisted.

The published HTML, CSS, JavaScript, images, and example-site content are public by design and can be downloaded by visitors. Include only material intended for the public demo. Theme names, repository names, refs, and workflow logs are also public. Restrict write access to this repository: a maintainer who can change its workflows can use its Actions secrets to read the configured private themes.

## References

- [Hugo build options](https://gohugo.io/commands/hugo/)
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
