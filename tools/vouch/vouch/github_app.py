"""Finish the GitHub App manifest flow: code → app id + private key → repository variable/secret.

    python3 -m vouch app finish <code> --repo owner/name

The one-time ``code`` comes from GitHub's redirect after "Create GitHub App" (see ui/app/index.html).
Stdlib for the exchange; ``gh`` for storing the id and key on the repository.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1]


def finish(code: str, repo: str) -> int:
    req = urllib.request.Request(f"https://api.github.com/app-manifests/{code}/conversions", method="POST",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "vouch",
                                          "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            app = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"GitHub refused the code ({e.code}): {e.read().decode()[:300]}", file=sys.stderr)
        print("Codes are single-use and expire after one hour — create the app again from ui/app/index.html.", file=sys.stderr)
        return 1
    app_id, slug, pem = app["id"], app["slug"], app["pem"]
    owner = app.get("owner", {}).get("login", "")
    pem_path = DEMO / "deploy" / "vouch-app.pem"
    pem_path.write_text(pem)
    os.chmod(pem_path, 0o600)
    (DEMO / "deploy" / "vouch-app.json").write_text(json.dumps(
        {"id": app_id, "slug": slug, "owner": owner, "html_url": app.get("html_url"), "name": app.get("name")}, indent=1))
    gi = DEMO / ".gitignore"
    txt = gi.read_text() if gi.exists() else ""
    for line in ("deploy/vouch-app.pem", "deploy/vouch-app.json"):
        if line not in txt:
            txt += line + "\n"
    gi.write_text(txt)

    ok = True
    for cmd, label in (
        (["gh", "variable", "set", "VOUCH_APP_ID", "-R", repo, "--body", str(app_id)], "variable VOUCH_APP_ID"),
        (["gh", "secret", "set", "VOUCH_APP_PRIVATE_KEY", "-R", repo, "--body", pem], "secret VOUCH_APP_PRIVATE_KEY"),
    ):
        res = subprocess.run(cmd, capture_output=True, text=True)
        print(("  set " if res.returncode == 0 else "  FAILED ") + label + ("" if res.returncode == 0 else f": {res.stderr.strip()}"))
        ok &= res.returncode == 0

    settings = (f"https://github.com/organizations/{owner}/settings/apps/{slug}" if app.get("owner", {}).get("type") == "Organization"
                else f"https://github.com/settings/apps/{slug}")
    print(f"\nVouch GitHub App created: id {app_id}, slug '{slug}', owner {owner}")
    print(f"  private key: {pem_path}")
    print("\nNext, in the browser:")
    print(f"  1. install on the repository:  https://github.com/apps/{slug}/installations/new")
    print(f"     → choose the organisation → Only select repositories → {repo.split('/')[-1]} → Install")
    print(f"  2. set the avatar:             {settings}  → Display information → upload")
    print(f"     {DEMO / 'integrations' / 'github' / 'app' / 'vouch-avatar.png'}")
    print("  3. re-run a PR workflow (or push) — comments now come from vouch[bot]")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="vouch app")
    sub = p.add_subparsers(dest="action", required=True)
    f = sub.add_parser("finish", help="exchange the manifest code and configure the repository")
    f.add_argument("code")
    f.add_argument("--repo", required=True)
    a = p.parse_args(argv)
    return finish(a.code, a.repo)
