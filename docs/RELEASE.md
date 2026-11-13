# Releasing qnx-porter to PyPI

Releases are published by [.github/workflows/release.yml](../.github/workflows/release.yml) when a tag
`v<version>` is pushed. It uses **PyPI Trusted Publishing**: PyPI trusts that one workflow in this
repository, so no API token exists in GitHub, in this repository or on anyone's machine.

The workflow builds the sdist and wheel, runs `twine check --strict`, installs the wheel in a fresh venv
and runs `qnx-porter selftest`, then uploads to https://pypi.org/project/qnx-porter/. It refuses to run if
the tag is not `v` + `__version__` from `qnx_porter/__init__.py`.

## One-time setup (a maintainer, in a browser)

### On pypi.org: add a pending trusted publisher
The project does not exist on PyPI yet, so it is registered as a *pending* publisher; the first release
creates the project and binds it to your account.

1. Open https://pypi.org and **Log in** (top right). If you have no account, **Register**, confirm your
   email, and turn on two-factor authentication (PyPI requires it to publish).
2. Click your username (top right) → **Your account**, then **Publishing** in the left menu.
   (Direct link: https://pypi.org/manage/account/publishing/)
3. Under **Add a new pending publisher**, select the **GitHub** tab.
4. Fill in exactly:

   | Field | Value |
   |---|---|
   | PyPI Project Name | `qnx-porter` |
   | Owner | `thegoodengineers` |
   | Repository name | `qnx-porter` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

5. Click **Add**. The publisher now shows under **Pending publishers**.

Release soon after this: a pending publisher does not reserve the name, and if someone else uploads a
project called `qnx-porter` first, it stops working.

### On github.com: create the `pypi` environment (recommended)
GitHub creates the environment by itself on the first run, but creating it first lets you limit it to tags:

1. Open https://github.com/thegoodengineers/qnx-porter → **Settings** → **Environments** → **New environment**.
2. Name: `pypi` → **Configure environment**.
3. Under **Deployment branches and tags**, choose **Selected branches and tags** → **Add deployment branch
   or tag rule** → Ref type **Tag** → pattern `v*` → **Add rule**.
4. Optional: tick **Required reviewers** and add yourself, so each release waits for one click of approval.

Do not add any secret to this environment. Trusted Publishing needs none.

## Releasing a version

```bash
git checkout main && git pull
python3 -c "import qnx_porter; print(qnx_porter.__version__)"   # must print the version you tag, e.g. 0.1.0
git tag v0.1.0 && git push origin v0.1.0
```

Then open **Actions** → **release** on GitHub and watch the run (approve it if you set required reviewers).
When both jobs are green, check from any machine:

```bash
python3 -m pip install --user qnx-porter
qnx-porter --help && qnx-porter selftest
```

## Next releases
1. Raise `__version__` in `qnx_porter/__init__.py` (the only place the version lives) in a pull request
   and merge it.
2. Tag that version on main as above: `git tag v0.1.1 && git push origin v0.1.1`.

PyPI never accepts the same version twice: to fix a version that is already on PyPI, raise the version and
tag again. If a run fails before the upload, fix it on main, then move the tag:
`git tag -f v0.1.0 && git push -f origin v0.1.0`.

## Build locally (optional, publishes nothing)
```bash
python3 -m venv /tmp/relvenv && /tmp/relvenv/bin/pip install build twine
/tmp/relvenv/bin/python -m build && /tmp/relvenv/bin/twine check --strict dist/*
```
