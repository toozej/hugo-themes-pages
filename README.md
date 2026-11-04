# Hugo theme demos

Build Hugo themes' `exampleSite` directories from private repositories and publish the rendered demos together on GitHub Pages.

**Demo index:** https://toozej.github.io/hugo-themes-pages/

| Theme | Source | Demo |
| --- | --- | --- |
| Folio | `toozej/hugo-theme-folio` (private) | https://toozej.github.io/hugo-themes-pages/folio/ |
| Folio Deluxe | `toozej/hugo-theme-folio-deluxe` (private) | https://toozej.github.io/hugo-themes-pages/folio-deluxe/ |

## How it works

[`themes.json`](themes.json) is the theme list. GitHub Actions checks out each theme at its configured branch, tag, or commit, installs its pinned Hugo Extended version, and builds its example site with `baseURL` set to `https://toozej.github.io/hugo-themes-pages/<slug>/`.

The builds run in parallel. A separate job collects only their generated `_site/<slug>/` directories, adds a demo index, and publishes one Pages artifact. Publication waits for every build to succeed; a failed theme build leaves the previous deployment intact.

Folio Deluxe uses Hugo Extended 0.168.0 and its own `scripts/build.py` wrapper to remove non-WebP output and run the theme's link, image, font, robots, and accessibility checks before publishing. Its temporary `exampleSite/public-pages/` output stays in the checkout; only the checked static files are copied into `_site/folio-deluxe/`.

Builds run when this repository receives a push to `main` or a `theme-updated` dispatch event. You can also start builds from **Actions → Build and deploy theme demos → Run workflow**. Each theme needs the sender workflow and token described below to report pushes to its `main` branch. Each accepted event rebuilds all themes at their configured refs and publishes the complete site. The workflow does not use the event payload to select a checkout ref.

The hourly schedule at minute 17 retries missed theme updates. GitHub may delay scheduled runs. GitHub disables scheduled workflows in inactive public repositories after 60 days. Push a change or enable the workflow again in Actions if this occurs. Pull requests validate only the public theme list. They never check out private source or receive deploy keys.

## Initial setup

1. In this repository, set **Settings → Pages → Build and deployment → Source** to **GitHub Actions**.
2. Give each private theme a separate **read-only deploy key**. For Folio:

   ```sh
   ssh-keygen -t ed25519 -C 'hugo-themes-pages:folio' -f folio-demo -N ''
   ```

   Add `folio-demo.pub` in **toozej/hugo-theme-folio → Settings → Deploy keys → Add deploy key**. Leave **Allow write access** unchecked.

3. Add the contents of `folio-demo` as an Actions repository secret named **`FOLIO_DEPLOY_KEY`** in **this public repository → Settings → Secrets and variables → Actions**. Never commit either private keys or theme checkouts. Once configured, keep the original key in a secure credential store or remove the local copy.
4. Run the deployment workflow and open the demo URL above.

Folio Deluxe uses a separate read-only deploy key registered in **toozej/hugo-theme-folio-deluxe → Settings → Deploy keys**. Store its private key in this repository's Actions secret **`FOLIO_DELUXE_DEPLOY_KEY`**. The original `FOLIO_DEPLOY_KEY` grants access only to Folio and cannot check out Deluxe.

The public repository's default `GITHUB_TOKEN` cannot read an unrelated private repository. Each deploy key supplies only that theme's Git read access. Deployment uses the workflow's short-lived Pages token. Theme push notifications use a separate token with write access only to this public repository. They do not need write access to a private theme.

## Theme push triggers

GitHub limits `push` triggers to the repository that contains the workflow. A push to a theme cannot directly start this repository's Pages workflow. Each theme must send a [`repository_dispatch` event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#repository_dispatch) instead.

1. Commit the receiving Pages workflow to this repository's `main` branch. GitHub requires the receiver to exist on the default branch.
2. Create a fine-grained personal access token for `toozej/hugo-themes-pages` only. Give it **Contents: Read and write**, as required by the [repository dispatch API](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event). The theme repository's `GITHUB_TOKEN` cannot send events to another repository.
3. Store the token as the Actions repository secret **`THEME_PAGES_DISPATCH_TOKEN`** in both `toozej/hugo-theme-folio` and `toozej/hugo-theme-folio-deluxe`.
4. Copy [`examples/notify-pages.yml`](examples/notify-pages.yml) to `.github/workflows/notify-pages.yml` in each theme repository. Commit each sender workflow to that theme's `main` branch.

Each sender runs on every push to `main`, including merges. It sends the theme repository, branch ref, and commit SHA. The receiver accepts only `refs/heads/main` from a repository that follows `main` in `themes.json`. Earlier pushes do not send events retroactively. Run the Pages workflow manually once to publish the current theme content.

The notification workflow fails with an error if its secret is absent. Renew the token in both themes before it expires. The hourly schedule remains available if notifications fail.

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
| `build_script` (optional) | Python build wrapper relative to the theme root, such as `scripts/build.py`. Without it, build directly with Hugo. |

A `build_script` wrapper must accept `--source`, `--destination`, `--base-url`, and `--check`. It must generate a complete static site in `public-pages/` directly under the supplied example-site directory. The publisher captures its diagnostics to keep private template excerpts out of public logs, validates its output, and copies only the rendered files into `_site/<slug>/`.

For a theme that follows `main`, configure the [theme push trigger](#theme-push-triggers) in its repository too.

If a future theme needs npm preprocessing, Hugo modules, submodules, or LFS, add those explicit setup steps before enabling it. Folio and Folio Deluxe need none of these.

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
