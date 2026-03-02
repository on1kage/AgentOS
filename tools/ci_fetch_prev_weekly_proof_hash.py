import io
import json
import os
import sys
import time
import zipfile
import urllib.request

API = "https://api.github.com"

def _fail(msg: str) -> int:
    sys.stdout.write(f"FAIL:{msg}\n")
    return 2

def _get_env(name: str) -> str:
    v = os.environ.get(name, "")
    if not v:
        raise RuntimeError(f"missing_env:{name}")
    return v

def _req_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def _req_bytes(url: str, token: str) -> bytes:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def main() -> int:
    try:
        repo = _get_env("GITHUB_REPOSITORY")
        token = _get_env("GITHUB_TOKEN")
        run_id = int(_get_env("GITHUB_RUN_ID"))
        workflow_file = os.environ.get("WEEKLY_PROOF_WORKFLOW_FILE", "weekly_proof_ci.yml")
        branch = os.environ.get("WEEKLY_PROOF_BRANCH", "main")
    except Exception as e:
        return _fail(f"env_error:{type(e).__name__}:{e}")

    url = f"{API}/repos/{repo}/actions/workflows/{workflow_file}/runs?status=completed&branch={branch}&per_page=20"
    try:
        runs = _req_json(url, token).get("workflow_runs", [])
    except Exception as e:
        return _fail(f"runs_fetch_error:{type(e).__name__}:{e}")

    prev = None
    for r in runs:
        try:
            rid = int(r.get("id"))
        except Exception:
            continue
        if rid == run_id:
            continue
        if str(r.get("conclusion")) != "success":
            continue
        prev = r
        break

    if prev is None:
        sys.stdout.write("NO_PREVIOUS_SUCCESS\n")
        return 0

    prev_id = int(prev["id"])
    aurl = f"{API}/repos/{repo}/actions/runs/{prev_id}/artifacts?per_page=100"
    try:
        artifacts = _req_json(aurl, token).get("artifacts", [])
    except Exception as e:
        return _fail(f"artifacts_fetch_error:{type(e).__name__}:{e}")

    target = None
    for a in artifacts:
        if str(a.get("name")) == "weekly_proof_hash":
            target = a
            break

    if target is None:
        sys.stdout.write("NO_PREVIOUS_ARTIFACT\n")
        return 0

    dl = target.get("archive_download_url")
    if not isinstance(dl, str) or not dl:
        return _fail("missing_archive_download_url")

    try:
        zbytes = _req_bytes(dl, token)
        zf = zipfile.ZipFile(io.BytesIO(zbytes))
        names = zf.namelist()
        want = None
        for n in names:
            if n.endswith("artifact_hash_run1.txt"):
                want = n
                break
        if want is None:
            return _fail("missing_artifact_hash_file_in_zip")
        content = zf.read(want).decode("utf-8").strip()
    except Exception as e:
        return _fail(f"artifact_download_error:{type(e).__name__}:{e}")

    if not content or any(c not in "0123456789abcdef" for c in content) or len(content) != 64:
        return _fail("invalid_hash_format")

    sys.stdout.write(content + "\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
