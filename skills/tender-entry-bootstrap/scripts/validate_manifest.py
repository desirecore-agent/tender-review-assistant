#!/usr/bin/env python3
"""Validate release-manifest.json against the tender-entry-bootstrap rules.

Standard library only. No network, no LLM, no platform imports, no DNS/SSRF
engine (URL checks are structural only: scheme/host/userinfo/whitespace).

fix-round-1 changes (E03):
  - all fixed-length SHA/format checks use re.fullmatch (no trailing-newline bypass),
  - team.url is parsed with urllib.parse: https only, valid hostname,
    no userinfo, no whitespace/control characters,
  - criticalAssets paths must be safe in-package relative paths
    (no absolute paths, no drive letters, no '..' segments, no backslashes),
  - released members must be complete: repoUrl, repoCommit, agentVersion,
    non-empty capabilities, non-empty criticalAssets with real hashes,
  - member objects reject unknown keys.

Structural validation cannot prove the remote repo exists or was reviewed;
publisher declarations are bound to the installed immutable Entry source.
Private assembly checks real publication receipts; this script does not authenticate QA. draft stays null/empty and never fakes values.

Exit codes: 0 = valid, 2 = invalid (violations printed), 3 = usage/IO error.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import json
import re
import sys
from urllib.parse import urlsplit

SCHEMA_ID = "tender-entry-bootstrap/release-manifest/v2"
PACKAGE_ID = "tender-entry-bootstrap"
ZERO_SHA40 = "0" * 40
ZERO_SHA64 = "0" * 64

RE_PKG_VERSION = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?")
RE_SHA40 = re.compile(r"[0-9a-f]{40}")
RE_SHA64 = re.compile(r"[0-9a-f]{64}")
RE_SLUG = re.compile(r"[\w-]+")
RE_CLIENT_VER = re.compile(r"\d+\.\d+\.\d+")
RE_HOSTNAME = re.compile(r"[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+")
# Unicode-aware segment: letters, digits, dots, hyphens, underscores (CJK etc. included)
RE_ASSET_SEGMENT = re.compile(r"[^/\x00-\x1f\\:]+")

TOP_FIELDS = {"manifestSchema", "packageId", "packageVersion", "status",
              "updatedAt", "minimumClientVersion", "platformRelease", "supportedHost", "team", "members"}
TEAM_FIELDS = {"url", "ref", "expectedCommit", "supervisorSlug"}
MEMBER_FIELDS = {"agentId", "slug", "repoUrl", "repoCommit", "agentVersion",
                 "capabilities", "criticalAssets", "delegationInputBinding"}
ASSET_FIELDS = {"path", "sha256"}


def fail(violations, msg):
    violations.append(msg)


def check_https_url(violations, obj, key, what, allow_null=False):
    """Structural HTTPS URL check (urllib.parse only; no DNS, no SSRF engine)."""
    v = obj.get(key)
    if v is None:
        if allow_null:
            return
        fail(violations, "missing required field: %s (%s)" % (key, what))
        return
    if not isinstance(v, str):
        fail(violations, "%s must be a string (%s)" % (key, what))
        return
    if any(ch.isspace() or ord(ch) < 0x20 for ch in v):
        fail(violations, "%s contains whitespace or control characters" % key)
        return
    try:
        parts = urlsplit(v)
    except ValueError:
        fail(violations, "%s is not a parseable URL" % key)
        return
    if parts.scheme != "https":
        fail(violations, "%s must use the https scheme" % key)
        return
    if parts.username is not None or parts.password is not None:
        fail(violations, "%s must not contain userinfo (credentials)" % key)
        return
    host = parts.hostname
    if not host or not RE_HOSTNAME.fullmatch(host):
        fail(violations, "%s has no valid hostname" % key)
        return
    if host.lower() in ("example.com", "example.org", "example.net") or \
       any(t in v for t in ("placeholder", "TODO", "REPLACE", "synthetic")):
        fail(violations, "%s looks like a placeholder; a real published URL is required" % key)
    # Explicit port validation: urlsplit only checks on .port access
    try:
        port = parts.port  # None = no port (ok); int = valid; raises ValueError on bad port
    except ValueError:
        fail(violations, "%s has a non-numeric or out-of-range port" % key)


def check_sha(violations, obj, key, what, equal_to=None):
    v = obj.get(key)
    if not isinstance(v, str) or len(v) != 40 or not RE_SHA40.fullmatch(v):
        fail(violations, "%s must be exactly 40 lowercase hex chars (%s)" % (key, what))
        return None
    if v == ZERO_SHA40:
        fail(violations, "%s must not be all zeros" % key)
        return None
    if equal_to is not None and isinstance(equal_to, str) and RE_SHA40.fullmatch(equal_to) and v != equal_to:
        fail(violations, "%s must equal team.ref (same pinned commit)" % key)
    return v


def check_asset_path(violations, p, tag):
    """Safe in-package relative path: no absolute, no drive, no '..', no backslash, no control chars, max 1024."""
    if not isinstance(p, str) or not p:
        fail(violations, "%s.path must be a non-empty string" % tag)
        return
    if len(p) > 1024:
        fail(violations, "%s.path exceeds max length 1024" % tag)
        return
    if p.startswith("/") or p.startswith("\\"):
        fail(violations, "%s.path must be relative inside the member repo" % tag)
        return
    if "\\" in p:
        fail(violations, "%s.path must not contain backslashes (drive/Windows paths are not allowed)" % tag)
        return
    if len(p) > 1 and p[1] == ":":
        fail(violations, "%s.path must not contain a drive letter" % tag)
        return
    if any(ord(ch) < 0x20 for ch in p):
        fail(violations, "%s.path contains control characters" % tag)
        return
    segs = p.split("/")
    for s in segs:
        if s == "":
            fail(violations, "%s.path has an empty segment" % tag)
            return
        if s in (".", ".."):
            fail(violations, "%s.path has a '.' or '..' segment (path escape refused)" % tag)
            return
        if not RE_ASSET_SEGMENT.fullmatch(s):
            fail(violations, "%s.path segment %r is not a safe filename" % (tag, s))
            return


def json_equal(a, b):
    """JSON deep equality: unordered object keys, ordered arrays, bool != number.

    Only contracts are compared; this deliberately never hashes private configs.
    """
    if isinstance(a, bool) or isinstance(b, bool): return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b and a == a and b == b and abs(a) != float('inf') and abs(b) != float('inf')
    if type(a) is not type(b): return False
    if isinstance(a, dict): return set(a) == set(b) and all(json_equal(a[k], b[k]) for k in a)
    if isinstance(a, list): return len(a) == len(b) and all(json_equal(x,y) for x,y in zip(a,b))
    return a == b


def validate_contract_binding(value, slug):
    if slug == 'tender-review-lead':
        return isinstance(value, dict) and value == {'kind':'absent'}
    if not isinstance(value, dict) or set(value) != {'kind','value'} or value.get('kind') != 'exact': return False
    contract = value['value']
    return isinstance(contract, dict) and set(contract) == {'version','schema'} and type(contract.get('version')) in (int,float) and contract['version'] == 1 and isinstance(contract['schema'], (dict,bool))


def validate(manifest):
    v = []
    if not isinstance(manifest, dict):
        fail(v, "manifest root must be an object")
        return v

    missing = TOP_FIELDS - set(manifest)
    if missing:
        fail(v, "missing top-level fields: %s" % sorted(missing))
    extra = set(manifest) - TOP_FIELDS
    if extra:
        fail(v, "unknown top-level fields: %s" % sorted(extra))

    if manifest.get("manifestSchema") != SCHEMA_ID:
        fail(v, "manifestSchema must equal %r" % SCHEMA_ID)
    if manifest.get("packageId") != PACKAGE_ID:
        fail(v, "packageId must equal %r" % PACKAGE_ID)

    pv = manifest.get("packageVersion")
    if not isinstance(pv, str) or not RE_PKG_VERSION.fullmatch(pv):
        fail(v, "packageVersion must be semver")
    status = manifest.get("status")
    if status not in ("draft", "released"):
        fail(v, "status must be 'draft' or 'released', got %r" % (status,))
    ua = manifest.get("updatedAt")
    if not isinstance(ua, str) or not ua:
        fail(v, "updatedAt must be a non-empty ISO 8601 timestamp string")

    mcv = manifest.get("minimumClientVersion")
    if mcv is not None:
        if not isinstance(mcv, str) or not RE_CLIENT_VER.fullmatch(mcv):
            fail(v, "minimumClientVersion must be null or X.Y.Z; never a guessed or unissued version")

    if manifest.get("supportedHost") != {"os": "darwin", "architecture": "arm64"}:
        fail(v, "supportedHost must be exactly darwin/arm64")
    release = manifest.get("platformRelease")
    if status == "draft":
        if release is not None or mcv is not None:
            fail(v, "draft keeps unknown platformRelease/minimumClientVersion null")
    elif status == "released":
        if not isinstance(release, dict):
            fail(v, "released requires publisher platformRelease binding")
        else:
            if set(release) != {"version", "sourceCommit", "artifactUrl", "artifactSha256"}:
                fail(v, "platformRelease requires exact public identity fields")
            if mcv is None or release.get("version") != mcv:
                fail(v, "platformRelease.version must equal non-null minimumClientVersion")
            check_sha(v, release, "sourceCommit", "published platform source")
            check_https_url(v, release, "artifactUrl", "published Mac archive")
            if release.get("artifactUrl") != "https://github.com/desirecore/agent-os/releases/download/v%s/DesireCore_arm64_%s.zip" % (mcv, mcv):
                fail(v, "platformRelease artifact must be exact version-bound official Mac archive")
            h = release.get("artifactSha256")
            if not isinstance(h, str) or not RE_SHA64.fullmatch(h) or h == ZERO_SHA64:
                fail(v, "platformRelease.artifactSha256 must be non-zero SHA256")

    team = manifest.get("team")
    members = manifest.get("members")

    if status == "draft":
        # Hard constraints: zero fork, zero network install.
        if "team" not in manifest or team is not None:
            fail(v, "draft manifest: team must be present and null (zero install)")
        if not isinstance(members, list) or len(members) != 0:
            fail(v, "draft manifest: members must be an empty array (zero install)")
        return v

    # ---- released branch: every reference must be real and complete ----
    if not isinstance(team, dict):
        fail(v, "released manifest: team must be an object with real publication references")
        team = {}
    extra_team = set(team) - TEAM_FIELDS
    if extra_team:
        fail(v, "unknown team fields: %s" % sorted(extra_team))
    check_https_url(v, team, "url", "real HTTPS team git URL")
    ref = check_sha(v, team, "ref", "no branch names, no HEAD")
    check_sha(v, team, "expectedCommit", "fork_team guard", equal_to=ref)
    sup = team.get("supervisorSlug")
    if not isinstance(sup, str) or not RE_SLUG.fullmatch(sup):
        fail(v, "released manifest: team.supervisorSlug must be the real supervisor slug")

    if not isinstance(members, list) or len(members) == 0:
        fail(v, "released manifest: members must list every team member (non-empty)")
        members = []
    seen = set()
    seen_ids = set()
    for i, m in enumerate(members):
        tag = "members[%d]" % i
        if not isinstance(m, dict):
            fail(v, "%s must be an object" % tag)
            continue
        extra_m = set(m) - MEMBER_FIELDS
        if extra_m:
            fail(v, "%s has unknown fields: %s" % (tag, sorted(extra_m)))
        identity = m.get("agentId")
        if not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", identity) or identity in seen_ids:
            fail(v, "%s.agentId must be a distinct immutable UUID" % tag)
        else:
            seen_ids.add(identity)
        slug = m.get("slug")
        if not isinstance(slug, str) or not RE_SLUG.fullmatch(slug):
            fail(v, "%s.slug must be a real agent slug" % tag)
        elif slug in seen:
            fail(v, "%s.slug duplicated: %s" % (tag, slug))
        else:
            seen.add(slug)
        if not validate_contract_binding(m.get("delegationInputBinding"), slug):
            fail(v, "%s.delegationInputBinding must declare Lead absence or the exact complete specialist contract" % tag)
        check_https_url(v, m, "repoUrl", "real member repo URL")
        check_sha(v, m, "repoCommit", "member repo pinned commit")
        av = m.get("agentVersion")
        if not isinstance(av, str) or not RE_PKG_VERSION.fullmatch(av):
            fail(v, "%s.agentVersion must be a real semver string" % tag)
        caps = m.get("capabilities")
        if not isinstance(caps, list) or len(caps) == 0 or not all(isinstance(c, str) and c for c in caps):
            fail(v, "%s.capabilities must be a non-empty list of strings" % tag)
        cas = m.get("criticalAssets")
        if not isinstance(cas, list) or len(cas) == 0:
            fail(v, "%s.criticalAssets must be a non-empty list (publication integrity requires it)" % tag)
            cas = []
        seen_assets = set()
        for j, ca in enumerate(cas):
            ctag = "%s.criticalAssets[%d]" % (tag, j)
            if not isinstance(ca, dict):
                fail(v, "%s must be an object" % ctag)
                continue
            extra_c = set(ca) - ASSET_FIELDS
            if extra_c:
                fail(v, "%s has unknown fields: %s" % (ctag, sorted(extra_c)))
            check_asset_path(v, ca.get("path"), ctag)
            if isinstance(ca.get("path"), str):
                if ca["path"] in seen_assets:
                    fail(v, "%s duplicate critical asset path" % ctag)
                seen_assets.add(ca["path"])
            h = ca.get("sha256")
            if not isinstance(h, str) or not RE_SHA64.fullmatch(h):
                fail(v, "%s.sha256 must be a lowercase 64-hex hash" % ctag)
            elif h == ZERO_SHA64:
                fail(v, "%s.sha256 must not be all zeros" % ctag)
    expected = {"tender-review-lead", "tender-review-requirements", "tender-review-evidence", "tender-review-commercial", "tender-review-visual"}
    if seen != expected or len(members) != 5 or team.get("supervisorSlug") != "tender-review-lead":
        fail(v, "released requires the exact five-role roster and Lead supervisor")
    return v


def main(argv):
    if len(argv) != 2:
        print("usage: validate_manifest.py <release-manifest.json>", file=sys.stderr)
        return 3
    try:
        with open(argv[1], "rb") as handle:
            raw = handle.read(1048577)
        if len(raw) > 1048576:
            raise ValueError("manifest exceeds 1 MiB")
        manifest = json.loads(raw)
        schema_raw = (Path(__file__).resolve().parent.parent / "schemas/release-manifest.schema.json").read_bytes()
    except (OSError, ValueError) as e:
        print(json.dumps({"status": "refused", "errors": [str(e)]}))
        return 3
    violations = validate(manifest)
    print(json.dumps({"status": "refused" if violations else "passed", "manifestSha256": hashlib.sha256(raw).hexdigest(), "schemaSha256": hashlib.sha256(schema_raw).hexdigest(), "publicationStatus": manifest.get("status") if isinstance(manifest, dict) else None, "validationMeaning": "structure_and_cross_fields_only_not_release_authentication_or_local_readiness", "errors": violations}, ensure_ascii=False))
    return 2 if violations else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
