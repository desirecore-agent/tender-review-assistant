#!/usr/bin/env python3
"""Read-only Mac local source checks. No installation, network or permission grant.

Roots/expected Entry commit/client version must come from current authorized
platform observations, not this manifest. Tool smoke, runtime dependencies,
rules confirmation and provenance of caller arguments remain caller duties.
This helper never emits ready/productionReady or authenticates tool execution.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
import tempfile
import resource
from validate_manifest import validate, json_equal

MAX_FILE = 4 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MANIFEST = 'skills/tender-entry-bootstrap/release-manifest.json'
class Refused(ValueError):
    pass

def identity(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

class Reader:
    def __init__(self):
        self.remaining = MAX_TOTAL
        self.deadline = time.monotonic() + 30
        self.snapshots = []
        self.roots = {}
        self.git_roots = {}
        self.git_snapshots = {}
    def check_time(self):
        if time.monotonic() >= self.deadline:
            raise Refused('internal_deadline_exceeded')
    def root(self, value):
        self.check_time()
        p = Path(value)
        if not p.is_absolute() or str(value).startswith('//') or '..' in p.parts:
            raise Refused('root_requires_authorized_absolute_path')
        if p not in self.roots:
            fd = self.open_absolute(p)
            self.roots[p] = fd
        return p
    def open_absolute(self, p):
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_DIRECTORY
        fd = os.open('/', flags)
        try:
            for part in p.parts[1:]:
                nxt = os.open(part, flags, dir_fd=fd)
                os.close(fd); fd = nxt
            return fd
        except BaseException:
            os.close(fd)
            raise
    def close(self):
        for fd in [*self.roots.values(), *self.git_roots.values()]:
            os.close(fd)
        self.roots.clear(); self.git_roots.clear()
        for temp in self.git_snapshots.values(): temp.cleanup()
        self.git_snapshots.clear()
    def __del__(self):
        self.close()
    def read(self, root, relative):
        self.check_time()
        parts = relative.split('/')
        if any(x in ('', '.', '..') for x in parts) or '\\' in relative or ':' in relative:
            raise Refused('unsafe_relative_path')
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        root = self.root(root)
        fd = os.dup(self.roots[root])
        try:
            for segment in parts[:-1]:
                nxt = os.open(segment, flags | os.O_DIRECTORY, dir_fd=fd)
                os.close(fd); fd = nxt
            leaf = os.open(parts[-1], flags, dir_fd=fd)
            try:
                before = os.fstat(leaf)
                if not stat.S_ISREG(before.st_mode) or before.st_size > min(MAX_FILE, self.remaining):
                    raise Refused('file_type_or_read_budget_refused')
                data = b''
                while len(data) < before.st_size:
                    self.check_time()
                    chunk = os.read(leaf, min(65536, before.st_size - len(data), self.remaining))
                    if not chunk:break
                    self.remaining -= len(chunk);data += chunk
                after = os.fstat(leaf)
                if identity(before) != identity(after) or len(data) != before.st_size:
                    raise Refused('source_changed_during_read')
                self.snapshots.append((root, relative, before))
                return data
            finally:
                os.close(leaf)
        finally:
            os.close(fd)
    def stable(self):
        # Re-open each original absolute path component without following links.
        for root, fd in self.roots.items():
            current = self.open_absolute(root)
            try:
                a, b = os.fstat(current), os.fstat(fd)
                if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):
                    raise Refused('root_changed_after_authorization')
            finally:
                os.close(current)
        previous = list(self.snapshots)
        for root, relative, old in previous:
            self.read(root, relative)
            if identity(self.snapshots[-1][2]) != identity(old):
                raise Refused('source_changed_after_read')
    def git(self, root, *args):
        self.check_time()
        root = self.root(root)
        if root not in self.git_roots:
            # Linked worktrees, symlinked git dirs and implicit parent discovery
            # are unsupported: never traverse a repository-supplied gitdir file.
            self.git_roots[root] = os.open('.git', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                           dir_fd=self.roots[root])
        gitfd = self.git_roots[root]
        if root not in self.git_snapshots:
            temp = tempfile.TemporaryDirectory(prefix='tender-git-identity-')
            self.git_snapshots[root] = temp
            dest = Path(temp.name)
            (dest / 'objects').mkdir(); (dest / 'refs').mkdir()
            count = [0]
            def copy_dir(fd, relative):
                if len(relative.split("/")) > 32: raise Refused("git_tree_depth_budget")
                for name in os.listdir(fd):
                    self.check_time()
                    count[0] += 1
                    if count[0] > 4096: raise Refused("git_tree_entry_budget")
                    path = relative + '/' + name
                    info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                    target = dest / path
                    if stat.S_ISDIR(info.st_mode):
                        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                        try:
                            target.mkdir(exist_ok=True)
                            copy_dir(child, path)
                        finally: os.close(child)
                    elif stat.S_ISREG(info.st_mode):
                        if path in ('objects/info/alternates', 'objects/info/http-alternates'):
                            raise Refused('external_git_object_store_unsupported')
                        target.write_bytes(self.read(root, '.git/' + path))
                    else: raise Refused('git_nonregular_object_refused')
            for name in ('HEAD', 'packed-refs'):
                try: data = self.read(root, '.git/' + name)
                except FileNotFoundError:
                    if name == 'HEAD': raise
                    continue
                (dest / name).write_bytes(data)
            for name in ('objects', 'refs'):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=gitfd)
                try: copy_dir(child, name)
                finally: os.close(child)
        # Git sees only a private bounded snapshot: no repository configuration,
        # hooks, filters, indexes, alternates or symlinks can reach the process.
        git_path = self.git_snapshots[root].name
        git = shutil.which('git')
        if not git: raise Refused('git_unavailable')
        env = {'PATH': os.defpath, 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_TERMINAL_PROMPT': '0',
               'GIT_NO_LAZY_FETCH': '1', 'GIT_OPTIONAL_LOCKS': '0', 'LC_ALL': 'C'}
        # These plumbing commands never read the worktree/index or run filters.
        # No diff/status/checkout/hash-object --path operations are permitted.
        def limits():
            resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FILE, MAX_FILE))
        with tempfile.TemporaryFile() as output:
            proc = subprocess.run([git, '--no-replace-objects',
                  '--git-dir=' + git_path, '-c', 'core.fsmonitor=false',
                  '-c', 'core.hooksPath=/dev/null', *args], env=env,
                  stdout=output, stderr=subprocess.DEVNULL, preexec_fn=limits,
                  timeout=min(5,max(.001,self.deadline-time.monotonic())), check=False)
            if proc.returncode: raise Refused('git_identity_unavailable')
            output.seek(0)
            return output.read(MAX_FILE)
    def committed_manifest(self, root, commit, raw):
        expected = self.git(root, 'rev-parse', '--verify', commit + ':' + MANIFEST).decode('ascii').strip()
        actual = hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\x00'+raw).hexdigest()
        if expected != actual:
            raise Refused('manifest_raw_bytes_differ_from_pinned_blob')
    def clean_sources(self, root):
        rows = self.git(root, 'ls-tree', '-rz', 'HEAD', '--', 'skills/tender-entry-bootstrap')
        if not rows or len(rows) > MAX_FILE: raise Refused('entry_tree_budget_or_empty')
        for row in rows.rstrip(b'\x00').split(b'\x00'):
            meta, name = row.split(b'\t', 1)
            mode, kind, oid = meta.split()
            if mode not in (b'100644', b'100755') or kind != b'blob':
                raise Refused('entry_nonregular_tracked_source')
            raw = self.read(root, name.decode('utf-8'))
            actual = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()
            if actual != oid.decode('ascii'):
                raise Refused('entry_tracked_skill_source_changed')
    def commit(self, root):
        value = self.git(root, 'rev-parse', '--verify', 'HEAD').decode('ascii').strip()
        if not re.fullmatch('[0-9a-f]{40}', value):
            raise Refused('installed_git_identity_unavailable')
        return value

def run(args):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise Refused('unsupported_host_requires_darwin_arm64')
    reader = Reader(); entry = reader.root(args.entry_root)
    if not re.fullmatch('[0-9a-f]{40}', args.expected_entry_commit) or set(args.expected_entry_commit)=={'0'}:
        raise Refused('expected_entry_commit_invalid')
    if reader.commit(entry) != args.expected_entry_commit:
        raise Refused('entry_commit_mismatch')
    reader.clean_sources(entry)
    raw = reader.read(entry, MANIFEST)
    reader.committed_manifest(entry, args.expected_entry_commit, raw)
    manifest = json.loads(raw)
    violations = validate(manifest)
    if violations:raise Refused('manifest_invalid: '+ '; '.join(violations))
    if manifest['status'] != 'released':raise Refused('draft_zero_install')
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.client_version):
        raise Refused('observed_client_version_invalid')
    version = lambda v: tuple(int(x) for x in v.split('.'))
    if version(args.client_version) < version(manifest['minimumClientVersion']):
        raise Refused('client_below_bound_minimum')
    roots = {}
    for slug, root in args.member:
        if slug in roots:raise Refused('duplicate_member_root')
        roots[slug] = reader.root(root)
    if set(roots) != {m['slug'] for m in manifest['members']}:
        raise Refused('installed_roster_mismatch')
    if len({(os.fstat(reader.roots[p]).st_dev,os.fstat(reader.roots[p]).st_ino) for p in roots.values()}) != len(roots):
        raise Refused('member_root_alias')
    entry_config=json.loads(reader.read(entry,'agent.json'))
    entry_seed=json.loads(reader.git(entry,'cat-file','blob',args.expected_entry_commit+':agent.json'))
    if not isinstance(entry_config,dict) or not isinstance(entry_seed,dict):
        raise Refused('entry_config_object_required')
    if 'delegation_input_contract' in entry_config or 'delegation_input_contract' in entry_seed:
        raise Refused('entry_contract_must_be_absent')
    facts=[]
    for m in manifest['members']:
        root=roots[m['slug']]
        if reader.commit(root) != m['repoCommit']:raise Refused('member_commit_mismatch')
        config=json.loads(reader.read(root,'agent.json'))
        if config.get('id') != m['agentId'] or config.get('version') != m['agentVersion']:
            raise Refused('member_identity_mismatch')
        binding=m['delegationInputBinding']
        committed_seed=json.loads(reader.git(root,'cat-file','blob',m['repoCommit']+':agent.json'))
        if not isinstance(committed_seed,dict):raise Refused('public_seed_object_required')
        if binding['kind']=='absent':
            if 'delegation_input_contract' in config or 'delegation_input_contract' in committed_seed:
                raise Refused('lead_contract_must_be_absent')
        elif not json_equal(committed_seed.get('delegation_input_contract'),binding['value']):
            raise Refused('contract_binding_differs_from_pinned_public_seed')
        elif not json_equal(config.get('delegation_input_contract'),binding['value']):
            raise Refused('installed_contract_drift')
        for asset in m['criticalAssets']:
            if hashlib.sha256(reader.read(root,asset['path'])).hexdigest() != asset['sha256']:
                raise Refused('critical_asset_mismatch')
        facts.append({'slug':m['slug'],'agentId':m['agentId'],'repoCommit':m['repoCommit'],'checkedAssets':len(m['criticalAssets']),'delegationInputBinding':binding['kind']})
    if reader.commit(entry) != args.expected_entry_commit:raise Refused('entry_commit_changed')
    for m in manifest['members']:
        if reader.commit(roots[m['slug']]) != m['repoCommit']:raise Refused('member_commit_changed')
    reader.clean_sources(entry)
    reader.stable()
    return {'status':'local_files_passed_tool_probes_required','manifestSha256':hashlib.sha256(raw).hexdigest(),'entryCommit':args.expected_entry_commit,'members':facts,'checkedHost':{'os':'darwin','architecture':'arm64'},'callerObservedClientVersion':args.client_version,'notVerified':['caller_argument_provenance','publisher_QA_authenticity','actual_Read_render_and_ExportMedia','member_owned_locked_runtime_and_formal_helpers','current_team_and_rules_confirmation','future_source_stability','official_contract_subset_current_platform_acceptance','business_results','production_acceptance']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entry-root',required=True)
    p.add_argument('--expected-entry-commit',required=True)
    p.add_argument('--client-version',required=True)
    p.add_argument('--member',nargs=2,action='append',default=[],metavar=('SLUG','AUTHORIZED_ROOT'))
    args=p.parse_args()
    try:
        result=run(args)
    except (Refused,OSError,ValueError,subprocess.TimeoutExpired) as e:
        print(json.dumps({'status':'blocked','errors':[str(e)]}));return 2
    print(json.dumps(result));return 0
if __name__=='__main__':
    sys.exit(main())
