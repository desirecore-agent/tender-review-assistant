#!/usr/bin/env python3
"""Local state helper for tender-entry-bootstrap (fix-round-1 rewrite).

Standard library only. No network, no LLM, no platform imports, no executing
commands from input. Handles ONLY:
  - locating/validating the fixed private state path (symlinks/escapes refused),
  - exclusive first-time initialization producing a LEGAL record,
  - cross-process CAS writes: an exclusive advisory lock covers the WHOLE
    "read current -> fully validate current -> compare revision -> validate
    candidate -> consistency check -> same-directory atomic replace" sequence,
  - structured conflict rejection (distinct exit codes).

The state file lives at <workspace>/.desirecore/tender-entry-bootstrap/state.json
where <workspace> is the entry agent's own registered private workspace. Never
write state into the skill's publication directory or any user tender folder.

State never stores credentials, user material bodies, or any "approval granted"
flag; rule approval is re-verified read-only against platform records on every use.

CLI (exactly as documented in docs/usage.md):
  init  <workspace-root> --manifest <release-manifest.json>
  read  <workspace-root>
  write <workspace-root> <new-state.json> --expected-revision N

Exit codes:
  0 ok
  2 invalid/corrupt state (syntactic OR semantic) -> recovery_required,
    scene preserved, never overwritten, never re-initialized
  3 usage error
  4 lock busy (another live writer holds the exclusive lock)
  5 revision conflict (CAS: disk revision != expected revision)
  6 state_path_unresolved (location/permissions/symlink problem)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile

if os.name == "nt":
    import msvcrt
else:
    import fcntl

STATE_REL = os.path.join(".desirecore", "tender-entry-bootstrap", "state.json")
LOCK_NAME = "state.lock"
STATE_SCHEMA_ID = "tender-entry-bootstrap/state/v1"
PACKAGE_ID = "tender-entry-bootstrap"

PHASES = {
    "uninitialized", "blocked", "ready_to_install", "installing",
    "waiting_rules_review", "ready", "upgrade_required", "recovery_required",
    "state_path_unresolved", "handoff_blocked",
}
SHA64 = re.compile(r"[0-9a-f]{64}")
SHA40 = re.compile(r"[0-9a-f]{40}")
SLUG = re.compile(r"[\w-]+")
BLOCK_CODE = re.compile(r"[a-z_]+")

TOP_FIELDS = {"stateSchema", "packageId", "manifestSha256", "revision", "phase", "updatedAt"}
OPTIONAL_TOP = {"attemptId", "blockedCodes", "install", "handoffRequest"}
INSTALL_FIELDS = {"teamId", "sourceCommit", "roster", "partial", "warnings", "verifiedAt"}
HANDOFF_FIELDS = {"requestId", "correlationId", "childRunId", "status", "materialRefs", "missingMaterials", "createdAt"}
MATREF_FIELDS = {"ref", "sha256", "readOnly"}

EXIT_OK, EXIT_INVALID_STATE, EXIT_USAGE, EXIT_LOCK_BUSY, EXIT_REVISION_CONFLICT, EXIT_PATH_UNRESOLVED = 0, 2, 3, 4, 5, 6


def out(msg, stream=sys.stdout):
    print(msg, file=stream)


# ---------------------------------------------------------------- path safety

def resolve_paths(workspace_root):
    """Resolve fixed state+lock paths; reject symlinks and escapes. Returns (state, lock, err)."""
    root = os.path.abspath(workspace_root)
    if not os.path.isdir(root):
        return None, None, "state_path_unresolved: workspace root does not exist or is not a directory"
    if os.path.islink(root):
        return None, None, "state_path_unresolved: workspace root is a symlink (refused)"
    cur = root
    for part in (".desirecore", "tender-entry-bootstrap"):
        cur = os.path.join(cur, part)
        if os.path.islink(cur):
            return None, None, "state_path_unresolved: path component %s is a symlink (refused)" % cur
        if os.path.exists(cur) and not os.path.isdir(cur):
            return None, None, "state_path_unresolved: %s exists but is not a directory" % cur
    state_path = os.path.join(root, STATE_REL)
    lock_path = os.path.join(os.path.dirname(state_path), LOCK_NAME)
    for p in (state_path, lock_path):
        if os.path.islink(p):
            return None, None, "state_path_unresolved: %s is a symlink (refused)" % p
    real_root = os.path.realpath(root)
    for p in (state_path, lock_path):
        if os.path.commonpath([real_root, os.path.realpath(p)]) != real_root:
            return None, None, "state_path_unresolved: resolved path escapes the workspace root"
    return state_path, lock_path, None


# ---------------------------------------------------------------- locking

def lock_open(lock_path):
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return os.open(lock_path, flags, 0o600)


def lock_acquire(fd):
    if os.name == "nt":
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def lock_release(fd):
    try:
        if os.name == "nt":
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        else:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def lock_holder_info(fd):
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        data = os.read(fd, 256).decode("utf-8", "replace").strip()
        return data or "unknown"
    except OSError:
        return "unknown"


# ---------------------------------------------------------------- validation

def validate_state(obj):
    """Full-structure validation of the finite state contract (syntactic+types+nested keys)."""
    v = []
    if not isinstance(obj, dict):
        return ["state root must be an object"]
    extra = set(obj) - (TOP_FIELDS | OPTIONAL_TOP)
    if extra:
        v.append("unknown top-level state fields: %s" % sorted(extra))
    for req in TOP_FIELDS:
        if req not in obj:
            v.append("missing required field: %s" % req)
    if obj.get("stateSchema") != STATE_SCHEMA_ID:
        v.append("stateSchema must equal %r" % STATE_SCHEMA_ID)
    if obj.get("packageId") != PACKAGE_ID:
        v.append("packageId must equal %r" % PACKAGE_ID)
    mh = obj.get("manifestSha256")
    if not isinstance(mh, str) or not SHA64.fullmatch(mh):
        v.append("manifestSha256 must be a lowercase 64-hex string (real value, no placeholders)")
    rev = obj.get("revision")
    if not isinstance(rev, int) or isinstance(rev, bool) or rev < 0:
        v.append("revision must be a non-negative integer")
    # type-first guards: catch wrong types BEFORE any `in`/hash/iteration
    if obj.get("phase") is not None and not isinstance(obj["phase"], str):
        v.append("phase must be a string (not %s)" % type(obj["phase"]).__name__)
    if obj.get("blockedCodes") is not None and not isinstance(obj["blockedCodes"], list):
        v.append("blockedCodes must be a list (not %s)" % type(obj["blockedCodes"]).__name__)
    inst = obj.get("install")
    if inst is not None and not isinstance(inst, dict):
        v.append("install must be null or an object (not %s)" % type(inst).__name__)
    hr = obj.get("handoffRequest")
    if hr is not None and not isinstance(hr, dict):
        v.append("handoffRequest must be null or an object (not %s)" % type(hr).__name__)
    if v:
        return v

    if obj.get("phase") not in PHASES:
        v.append("phase must be one of: %s" % ", ".join(sorted(PHASES)))
    ua = obj.get("updatedAt")
    if not isinstance(ua, str) or not ua:
        v.append("updatedAt must be a non-empty ISO 8601 string")
    if "attemptId" in obj and obj["attemptId"] is not None and not isinstance(obj["attemptId"], str):
        v.append("attemptId must be string or null")
    bc = obj.get("blockedCodes")
    if not isinstance(bc, list) or not all(isinstance(c, str) and BLOCK_CODE.fullmatch(c) for c in bc):
        v.append("blockedCodes must be a list of [a-z_]+ codes")

    if inst is not None:
        if not isinstance(inst, dict):
            v.append("install must be null or an object")
        else:
            extra_i = set(inst) - INSTALL_FIELDS
            if extra_i:
                v.append("install has unknown fields: %s" % sorted(extra_i))
            if not isinstance(inst.get("teamId"), str) or not inst["teamId"]:
                v.append("install.teamId required and non-empty")
            sc = inst.get("sourceCommit")
            if not isinstance(sc, str) or not SHA40.fullmatch(sc):
                v.append("install.sourceCommit must be a 40-hex SHA")
            ro = inst.get("roster")
            if not isinstance(ro, list) or not ro or not all(isinstance(s, str) and SLUG.fullmatch(s) for s in ro):
                v.append("install.roster must be a non-empty list of slugs")
            if not isinstance(inst.get("verifiedAt"), str) or not inst["verifiedAt"]:
                v.append("install.verifiedAt required (non-empty)")
            if "partial" in inst and not isinstance(inst["partial"], bool):
                v.append("install.partial must be boolean")
            if "warnings" in inst:
                wn = inst["warnings"]
                if not isinstance(wn, list) or not all(isinstance(w, str) for w in wn):
                    v.append("install.warnings must be a list of strings")

    hr = obj.get("handoffRequest")
    if hr is not None:
        if not isinstance(hr, dict):
            v.append("handoffRequest must be null or an object")
        else:
            extra_h = set(hr) - HANDOFF_FIELDS
            if extra_h:
                v.append("handoffRequest has unknown fields: %s" % sorted(extra_h))
            if not isinstance(hr.get("requestId"), str) or not hr["requestId"]:
                v.append("handoffRequest.requestId required and non-empty")
            if hr.get("status") not in ("prepared", "dispatched", "handoff_blocked"):
                v.append("handoffRequest.status invalid")
            for cid in ("correlationId", "childRunId"):
                if cid in hr and hr[cid] is not None and not isinstance(hr[cid], str):
                    v.append("handoffRequest.%s must be string or null" % cid)
            mr = hr.get("materialRefs")
            if mr is not None and not isinstance(mr, list):
                v.append("handoffRequest.materialRefs must be a list (not %s)" % type(mr).__name__)
            elif mr is not None:
                for i, m in enumerate(mr):
                    mtag = "handoffRequest.materialRefs[%d]" % i
                    if not isinstance(m, dict):
                        v.append("%s must be an object" % mtag)
                        continue
                    extra_mr = set(m) - MATREF_FIELDS
                    if extra_mr:
                        v.append("%s has unknown fields: %s (material bodies/approval flags are forbidden)" % (mtag, sorted(extra_mr)))
                    ref = m.get("ref")
                    if not isinstance(ref, str) or not ref:
                        v.append("%s.ref required and non-empty" % mtag)
                    elif ref.startswith("~") or not (ref.startswith("/") or ref.startswith("dc-media://")):
                        v.append("%s.ref must be an absolute path or dc-media pointer" % mtag)
                    if "sha256" in m and m["sha256"] is not None and (not isinstance(m["sha256"], str) or not SHA64.fullmatch(m["sha256"])):
                        v.append("%s.sha256 must be null or 64-hex" % mtag)
                    if "readOnly" in m and not isinstance(m["readOnly"], bool):
                        v.append("%s.readOnly must be boolean" % mtag)
            mm = hr.get("missingMaterials")
            if mm is not None and (not isinstance(mm, list) or not all(isinstance(x, str) for x in mm)):
                v.append("handoffRequest.missingMaterials must be a list of strings")
            if not isinstance(hr.get("createdAt"), str) or not hr["createdAt"]:
                v.append("handoffRequest.createdAt required (non-empty)")
    return v


def check_consistency(obj):
    """Record self-consistency (NOT an authorization system; real re-verification still required every use)."""
    v = []
    phase = obj.get("phase")
    inst = obj.get("install")
    bc = obj.get("blockedCodes") or []
    if phase == "ready":
        if inst is None:
            v.append("consistency: phase=ready requires a real install record (install is null)")
        elif inst.get("partial"):
            v.append("consistency: phase=ready contradicts install.partial=true")
        if bc:
            v.append("consistency: phase=ready contradicts non-empty blockedCodes %s" % bc)
    if phase == "waiting_rules_review" and inst is None:
        v.append("consistency: phase=waiting_rules_review requires an install record")
    if phase == "installing" and not obj.get("attemptId"):
        v.append("consistency: phase=installing requires attemptId")
    if phase == "blocked" and not bc:
        v.append("consistency: phase=blocked requires non-empty blockedCodes")
    if phase == "handoff_blocked" and obj.get("handoffRequest") is None:
        v.append("consistency: phase=handoff_blocked requires a handoffRequest record")
    return v


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def atomic_write(path, obj):
    """Same-directory random exclusive temp file (mkstemp, O_EXCL) + fsync + os.replace."""
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        # Only ever remove a temp file this call owns.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------- commands

def cmd_init(args):
    state_path, lock_path, err = resolve_paths(args.workspace_root)
    if err:
        out("ERROR: %s" % err, sys.stderr)
        return EXIT_PATH_UNRESOLVED
    if os.path.exists(state_path):
        out("ERROR: init refused: state already exists at %s (exclusive init; preserve existing state)" % state_path, sys.stderr)
        return EXIT_INVALID_STATE
    try:
        mf = load_json(args.manifest)
    except (OSError, json.JSONDecodeError) as e:
        out("ERROR: cannot read manifest for init: %s" % e, sys.stderr)
        return EXIT_USAGE
    if not isinstance(mf, dict) or mf.get("packageId") != PACKAGE_ID:
        out("ERROR: manifest is not a %s release manifest" % PACKAGE_ID, sys.stderr)
        return EXIT_USAGE
    with open(args.manifest, "rb") as f:
        manifest_sha = hashlib.sha256(f.read()).hexdigest()
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    lock_fd = lock_open(lock_path)
    if not lock_acquire(lock_fd):
        out("ERROR: lock busy during init (holder: %s); recovery_required, not forcing" % lock_holder_info(lock_fd), sys.stderr)
        lock_release(lock_fd)
        return EXIT_LOCK_BUSY
    try:
        if os.path.exists(state_path):
            out("ERROR: init refused: concurrent init detected", sys.stderr)
            return EXIT_INVALID_STATE
        skeleton = {
            "stateSchema": STATE_SCHEMA_ID,
            "packageId": PACKAGE_ID,
            "manifestSha256": manifest_sha,
            "revision": 0,
            "phase": "uninitialized",
            "blockedCodes": [],
            "attemptId": None,
            "install": None,
            "handoffRequest": None,
            "updatedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        own = validate_state(skeleton)
        if not own:
            own = check_consistency(skeleton)
        if own:
            out("ERROR: internal error: init skeleton failed self-validation: %s" % own, sys.stderr)
            return EXIT_INVALID_STATE
        atomic_write(state_path, skeleton)
    finally:
        lock_release(lock_fd)
    out("INITIALIZED: %s (manifestSha256=%s)" % (state_path, manifest_sha))
    return EXIT_OK


def cmd_read(args):
    state_path, lock_path, err = resolve_paths(args.workspace_root)
    if err:
        out("ERROR: %s" % err, sys.stderr)
        return EXIT_PATH_UNRESOLVED
    if not os.path.exists(state_path):
        out("NO_STATE at %s" % state_path)
        return EXIT_OK
    lock_fd = lock_open(lock_path)
    if not lock_acquire(lock_fd):
        out("ERROR: lock busy during read (holder: %s); retry later, never force" % lock_holder_info(lock_fd), sys.stderr)
        lock_release(lock_fd)
        return EXIT_LOCK_BUSY
    try:
        try:
            obj = load_json(state_path)
        except (OSError, json.JSONDecodeError) as e:
            out("ERROR: recovery_required: state unreadable/corrupt at %s: %s (scene preserved; do not re-init)" % (state_path, e), sys.stderr)
            return EXIT_INVALID_STATE
        violations = validate_state(obj)
        if not violations:
            violations = check_consistency(obj)
        if violations:
            out("ERROR: recovery_required: existing state is semantically invalid (%d issue(s)); scene preserved, not overwritten:" % len(violations), sys.stderr)
            for x in violations:
                out("  - %s" % x, sys.stderr)
            return EXIT_INVALID_STATE
        out(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))
    finally:
        lock_release(lock_fd)
    return EXIT_OK


def cmd_write(args):
    state_path, lock_path, err = resolve_paths(args.workspace_root)
    if err:
        out("ERROR: %s" % err, sys.stderr)
        return EXIT_PATH_UNRESOLVED
    if not os.path.exists(state_path):
        out("ERROR: write refused: no existing state at %s (run init first)" % state_path, sys.stderr)
        return EXIT_INVALID_STATE
    lock_fd = lock_open(lock_path)
    if not lock_acquire(lock_fd):
        out("ERROR: lock busy (holder: %s); structured conflict: do not retry blindly; if holder is a crashed/unknown writer this is recovery_required, preserve the scene" % lock_holder_info(lock_fd), sys.stderr)
        lock_release(lock_fd)
        return EXIT_LOCK_BUSY
    try:
        # Whole CAS sequence happens under the exclusive lock.
        try:
            current = load_json(state_path)
        except (OSError, json.JSONDecodeError) as e:
            out("ERROR: recovery_required: existing state unreadable/corrupt: %s (scene preserved)" % e, sys.stderr)
            return EXIT_INVALID_STATE
        cur_viol = validate_state(current)
        if not cur_viol:
            cur_viol = check_consistency(current)
        if cur_viol:
            out("ERROR: recovery_required: existing state semantically invalid (%d issue(s)); refusing to overwrite; scene preserved:" % len(cur_viol), sys.stderr)
            for x in cur_viol:
                out("  - %s" % x, sys.stderr)
            return EXIT_INVALID_STATE
        cur_rev = current["revision"]
        if cur_rev != args.expected_revision:
            out("ERROR: REVISION_CONFLICT: disk revision %s != expected %s (concurrent write or external edit; refusing to overwrite)" % (cur_rev, args.expected_revision), sys.stderr)
            return EXIT_REVISION_CONFLICT
        try:
            new_obj = load_json(args.new_state_file)
        except (OSError, json.JSONDecodeError) as e:
            out("ERROR: cannot read new state payload: %s" % e, sys.stderr)
            return EXIT_USAGE
        violations = validate_state(new_obj)
        if not violations:
            violations = check_consistency(new_obj)
        if violations:
            out("INVALID new state (%d):" % len(violations), sys.stderr)
            for x in violations:
                out("  - %s" % x, sys.stderr)
            return EXIT_INVALID_STATE
        if new_obj["revision"] != args.expected_revision + 1:
            out("ERROR: new revision must equal expected_revision + 1 (monotonic CAS)", sys.stderr)
            return EXIT_REVISION_CONFLICT
        os.lseek(lock_fd, 0, os.SEEK_SET)
        os.ftruncate(lock_fd, 0)
        os.write(lock_fd, ("pid=%d" % os.getpid()).encode("ascii"))
        atomic_write(state_path, new_obj)
    finally:
        lock_release(lock_fd)
    out("WRITTEN: %s revision=%d phase=%s" % (state_path, new_obj["revision"], new_obj["phase"]))
    return EXIT_OK


# ---------------------------------------------------------------- argparse

def build_parser():
    p = argparse.ArgumentParser(
        prog="state_tool.py",
        description="tender-entry-bootstrap private state helper (stdlib only).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("init", help="exclusive first-time initialization (requires a real manifest)")
    pi.add_argument("workspace_root", help="entry agent's registered private workspace root")
    pi.add_argument("--manifest", required=True, help="path to release-manifest.json (real sha256 is recorded)")
    pi.set_defaults(func=cmd_init)

    pr = sub.add_parser("read", help="read and FULLY validate the current state")
    pr.add_argument("workspace_root")
    pr.set_defaults(func=cmd_read)

    pw = sub.add_parser("write", help="CAS write under an exclusive cross-process lock")
    pw.add_argument("workspace_root")
    pw.add_argument("new_state_file", help="file containing the full candidate state JSON")
    pw.add_argument("--expected-revision", required=True, type=int,
                    help="revision currently expected on disk (CAS guard)")
    pw.set_defaults(func=cmd_write)
    return p


def main(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse exits 2 on bad usage; normalize to our usage code.
        return EXIT_USAGE if e.code != 0 else EXIT_OK
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
