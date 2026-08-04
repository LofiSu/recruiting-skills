# GitHub Pages publication

Publish the completed local report without adding generated reports to `main`.
The publication target is:

```text
branch: gh-pages
file:   <arxiv-id>/index.html
URL:    https://<owner>.github.io/<repository>/<arxiv-id>/
home:   https://<owner>.github.io/<repository>/
```

## Preconditions

Attempt automatic publication only when all of these are true:

1. the report exists at `outputs/<arxiv-id>/report.html`;
2. `origin` identifies a GitHub repository;
3. the host has an already-authorized GitHub write tool or Git credential;
4. the host policy permits the requested repository write.

Never ask for a password or print a token. Do not turn publication failure into
a dependency-install request. If a precondition is missing, return the local
report and name the missing capability.

## Isolation rule

Do not switch the user's source checkout to `gh-pages`. Use a temporary clone,
temporary worktree, or an equivalent GitHub content/branch API. Preserve every
existing file already published on `gh-pages`.

The only report-specific change is:

```text
<arxiv-id>/index.html
```

A branch-level `.nojekyll` file is allowed. Do not copy `outputs/`, source code,
local caches, logs, credentials, or unrelated reports from the source checkout.

## Git-capable host

Adapt these commands to the host shell. Treat all shown variables as data, not
as shell source:

```sh
report="outputs/<arxiv-id>/report.html"
remote_url="$(git remote get-url origin)"
site_dir="$(mktemp -d)/site"

if git ls-remote --exit-code --heads "$remote_url" gh-pages >/dev/null 2>&1; then
  git clone --depth 1 --single-branch --branch gh-pages "$remote_url" "$site_dir"
else
  git clone --no-checkout "$remote_url" "$site_dir"
  (
    cd "$site_dir"
    git switch --orphan gh-pages
  )
fi

mkdir -p "$site_dir/<arxiv-id>"
cp "$report" "$site_dir/<arxiv-id>/index.html"
: > "$site_dir/.nojekyll"
python3 scripts/build_pages_index.py "$site_dir"

(
  cd "$site_dir"
  git add .nojekyll index.html "<arxiv-id>/index.html"
  if ! git diff --cached --quiet; then
    git commit -m "publish: update <arxiv-id> report"
    git push origin gh-pages
  fi
)
```

Use a safely generated temporary directory and remove it after publication.
Never interpolate an unvalidated paper identifier into a path. Accept only an
arXiv identifier composed of ASCII digits, dots, and an optional `v` plus digits.

## GitHub API-capable host

When Git shell access is unavailable but a GitHub tool can create commits:

1. read the `gh-pages` branch head when it exists;
2. preserve the existing branch tree and create or update
   `<arxiv-id>/index.html`;
3. enumerate safe report directories already present on the branch and render
   root `index.html` from `assets/pages-index-template.html` with the same
   escaped, sorted relative links produced by `scripts/build_pages_index.py`;
4. include `.nojekyll` when initializing the branch;
5. commit the report and root homepage to `gh-pages`;
6. configure GitHub Pages with branch `gh-pages` and path `/` when the tool
   exposes repository Pages settings.

If the host tool cannot configure Pages, publish the branch and tell the user
that repository Pages must be set once to **Deploy from a branch → gh-pages → /**
before the URL becomes available.

## Configure Pages

When authenticated GitHub CLI access exists, inspect Pages first:

```sh
gh api "repos/<owner>/<repository>/pages"
```

If Pages does not exist, create it with `gh-pages` as the branch source. If it
exists with another source, update it only when the current request authorizes
that repository setting change. Repository owners can always configure the same
setting at:

```text
Settings → Pages → Build and deployment → Deploy from a branch
Branch: gh-pages / (root)
```

## Verification

After a successful push, derive the report URL and collection homepage URL from
the actual GitHub owner and repository name. Request both URLs with bounded
retries.

Publication is verified only when:

- the response is HTTP `200`; and
- the returned HTML contains the exact escaped paper title or arXiv identifier.

The collection homepage is verified only when it returns HTTP `200` and
contains both `researcher-recruiting-skill` and `research-talent-scout`.

GitHub Pages deployment is asynchronous and may take tens of seconds on a first
publish. Keep retries bounded. If verification times out, return the local report,
state that the branch push succeeded but deployment is still pending, and do not
describe the URL as live.
