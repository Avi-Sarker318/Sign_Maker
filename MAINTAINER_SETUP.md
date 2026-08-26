# Maintainer setup (for you, one time)

This gets your code onto GitHub and set up so that pushing a version tag
automatically builds a Windows `.exe` (handling both Sticky Signs and
Hanging Signs) and publishes it — free, using GitHub's own build machines.
Nobody, including you, needs a Windows PC to build it.

## 1. Create the GitHub repo

1. Go to https://github.com/new
2. Name it something like `sign-maker` (any name works).
3. Choose **Public** (required for free unlimited GitHub Actions minutes —
   private repos also get 2,000 free minutes/month, plenty for this, but
   public is simplest and this build takes under a minute).
4. Don't add a README/gitignore/license from GitHub's UI — you already have
   these files locally. Click **Create repository**.

## 2. Push this folder to it

From inside this folder, run:

```bash
git init
git add .
git commit -m "Sign Maker: Sticky + Hanging Signs, GUI, and auto-build workflow"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/sign-maker.git
git push -u origin main
```

(Replace `YOUR-USERNAME` and the repo name with your actual values.)

## 3. Cut your first release

Tag a version and push the tag — this is what triggers the Windows build:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Then:

1. Go to your repo's **Actions** tab on GitHub. You'll see "Build Windows app"
   running (takes about 1–2 minutes).
2. Once it's green, go to the **Releases** page (right sidebar of the repo,
   or `github.com/YOUR-USERNAME/sign-maker/releases`).
3. GitHub has automatically created a release with **SignMaker.exe**
   attached, built fresh from your source. It handles both sign types - one
   app, one download.

Send employees the link to that Releases page (or the direct `.exe` link).
They just need the README.md instructions — no Python, no installer, no cost.

## 4. Shipping updates later

Whenever you change `sign_maker_gui.py`, `sticky_signs_core.py`,
`hanging_signs_core.py`, or `signs_common.py`:

```bash
git add .
git commit -m "describe your change"
git push
git tag v1.0.1
git push origin v1.0.1
```

A new `.exe` gets built and published automatically under the new tag. Tell
employees to grab the new one from Releases when they need the update — there's
no auto-update built in, since that would add real complexity for zero cost
savings here.

## Notes

- `workflow_dispatch` is also enabled in the workflow, so you can manually
  re-run a build from the **Actions** tab without pushing a new tag, if you
  just want to test the build itself.
- Everything here is free: public GitHub repos, GitHub Actions minutes on
  public repos, and GitHub Releases all have no cost.
- If you'd rather not use GitHub Releases at all, the workflow also uploads
  the same `.exe` as a plain **build artifact** on every run (visible under
  the Actions tab → the specific run → Artifacts), which you could zip and
  distribute another way (email, shared drive, etc).

## Generating signs entirely from GitHub - no computer needed

Beyond building the Windows app, this repo can generate the actual sign
PDFs by itself, for both sign types, using two more GitHub Actions. This
means anyone with access to the repo can add labels and get PDFs from a
phone browser, a Mac, a locked-down work PC - nothing to install, ever.

How it fits together:

- **`signs/sticky-labels.txt`** and **`signs/hanging-labels.txt`** are the
  master lists for each sign type, tracked in the repo like any other file
  (so you get a full history of who added what, for free, via `git log`).
- **"Update sign labels"** (`.github/workflows/update-labels.yml`) lets you
  add to either list from the Actions tab, no git required - you pick which
  sign type from a dropdown.
- **"Build & publish signs"** (`.github/workflows/build-signs.yml`) notices
  whenever either label file changes - from either of the two ways below -
  and rebuilds that sign type's PDFs, publishing them to their own stable
  Release: **"Latest Sticky Signs"** or **"Latest Hanging Signs"**. Those
  links never change, so bookmark them once.

### One-time setup

1. Push this repo to GitHub as described above - the workflow files and the
   two seed label files are already included.
2. Go to **Settings → Actions → General → Workflow permissions** and choose
   **"Read and write permissions"**. This is required - without it, the
   workflows can't commit the updated label list or publish the release.
   (Some organizations set repos to read-only by default.)

### Adding labels, going forward - two ways

**Option A - fill in a form (recommended for most people):**

1. Go to the **Actions** tab → **"Update sign labels"** → **Run workflow**.
2. Choose **sign_type**: `sticky` or `hanging`.
3. Type your labels/ranges into the **add_labels** box, e.g.
   `2-031:035, 2-040:047`. Ranges and multiple prefixes both work.
4. Click the green **Run workflow** button.
5. Wait about 30-60 seconds, then go to the **Releases** page - the
   matching release (**"Latest Sticky Signs"** or **"Latest Hanging
   Signs"**) now has the updated, complete, correctly sorted PDFs.

Check **start_new** in that same form instead of add_labels if you want to
throw away that sign type's current list and start a completely different
batch. It only affects the one you picked - the other sign type's list is
untouched.

**Option B - edit the file directly:**

1. Open `signs/sticky-labels.txt` or `signs/hanging-labels.txt` in the repo
   on GitHub, depending on which you want.
2. Click the pencil (✏️) icon to edit.
3. Add a line (or several), e.g. `2-036:039`, and commit the change.
4. The "Build & publish signs" workflow fires automatically - check the
   matching Release page in about a minute.

Both options end up in the same place: one always-current PDF per prefix,
per sign type, sorted by number regardless of what order things were added
in, available at the same two Releases links every time.

## Giving people a link they can just open - no download, no GitHub account

Everything above (the `.exe`, and the GitHub Actions pipeline) still means
someone downloads a file at the end. If you want people to open a link and
use the tool directly in their browser - nothing downloaded, ever, not even
a PDF until they choose to - there's a web version in the `docs/` folder,
built with plain HTML/JavaScript (no Python, no server). It's hosted for
free with **GitHub Pages**, directly from this same repo.

This isn't a lightweight copy of the desktop app - it's the same barcode
encoding, the same PDF layout math, and the same live preview, just running
entirely inside the visitor's browser instead of on a downloaded program.
Every label they add, every PDF generated, and the barcodes themselves are
built client-side; nothing is ever uploaded anywhere.

### One-time setup

1. Push this repo to GitHub as described above - the `docs/` folder is
   already included.
2. Go to **Settings \u2192 Pages** (left sidebar).
3. Under **Build and deployment \u2192 Source**, choose **"Deploy from a
   branch"**.
4. Under **Branch**, choose **main** and **/docs**, then click **Save**.
5. Wait about 1 minute, then refresh the page - GitHub shows you the live
   URL, something like `https://your-username.github.io/sign-maker/`. Send
   that link to anyone. They open it in any browser, on any device, and can
   start adding labels immediately.

### What's different about the web version

- **No install, ever** - not Python, not the app, nothing. Just a link.
- **Never sleeps, no cold start** - unlike a hosted Python app, a GitHub
  Pages site is just static files. It loads instantly, every time.
- **Your label list is remembered per-device** - it's saved in that
  browser's local storage, so closing the tab and coming back later on the
  *same device* still has everything you added. (A different device or
  browser starts fresh, since there's no shared account or database - this
  is a static site, not a multi-user service.)
- **Nothing is ever sent to a server** - barcode generation and PDF creation
  both happen entirely on the visitor's own device. This is actually more
  private than a hosted Python app, since there's no server in the loop at
  all after the page first loads.
- Updating it later is automatic-ish: push a change to anything in `docs/`
  and the live site updates within a minute or two of GitHub Pages
  rebuilding - no dashboard, no redeploy button, nothing else needed.

### How it works, if you're curious

`docs/js/code128.js` is a from-scratch Code128 barcode encoder (the same
standard barcode format the Python `python-barcode` library produces) -
verified to generate correct, genuinely scannable barcodes. `docs/js/sign-
layout.js` ports the exact same page-layout measurements from
`sticky_signs_core.py` and `hanging_signs_core.py` into JavaScript, using
the `jsPDF` library (vendored locally in `docs/js/vendor/`, not loaded from
a CDN, so the site has zero external dependencies) to actually draw the
PDF pages. `docs/js/app.js` is the page logic - the sign-type switcher,
Quick Add, and the download flow, which bundles each prefix's PDF into one
`.zip` using the `JSZip` library (also vendored locally).

