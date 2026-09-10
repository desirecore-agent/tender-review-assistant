# Usage

## What this is

`tender-entry-bootstrap` is the first-use bootstrap skill of the tender review entry agent. It does exactly four things: verify install conditions → perform one controlled install of the correct review-team version → explicitly wait for human rule approval → hand the real request and materials off to the lead reviewer. The entry itself does **no** professional tender review and gives **no** compliance/winning guarantees.

## First-use flow

1. **Locate state**: `ManageWorkDirs(action="list", scope="current")` finds the entry's own registered private workspace (user ID comes from platform-injected identity — never guessed, never scanning other users' dirs). The state file is fixed at `<workspace>/.desirecore/tender-entry-bootstrap/state.json`. Switching primary workspace does not migrate state; a removed default dir ⇒ `state_path_unresolved` — never substitute an arbitrary project dir.
2. Release binding and preflight: follow the layered checks below and SKILL section 2.
3. Run the actual PDF/ExportMedia smoke below, never writing test output into the publication directory.
4. **Manifest check**: `python3 scripts/validate_manifest.py release-manifest.json`. Current manifest is `draft` ⇒ zero install, diagnostics only.
5. **Install (released only)**: See SKILL.md §4. Before fork, persist the `attemptId` (must succeed before continuing); after fork, immediately persist the receipt; success but with failed members/warnings ⇒ `partial`; lost receipt/unknown origin ⇒ `recovery_required`.
6. **Rule approval**: `waiting_rules_review`. User enters the lead session from the sidebar, uses the lead avatar (TL) entry to open the **target team group's** settings (with multiple teams, never use the old MoreMenu first team), verifies name + real teamId, reviews and confirms rules. Entry read-only checks existing records; never writes, deletes, or simulates approval files. Entry re-verifies install and governance facts on every use; does not automatically re-review old professional reports — each new review request is handled by the team from scratch.
7. **Hand-off**: Once `ready`, build a private request list (coordinates and hashes only, no content), default `Delegate(handoff=true, teamId=<verified>, task=<first-person restatement>)`. Target busy/rejected/unknown ⇒ `handoff_blocked`, keep request, do not dispatch a second copy.

## Release and local capability boundary

`released` means published immutable source, not production qualification. Publisher QA is checked by private assembly; current Entry checks the publisher declaration bound to its actual installed commit. It does not independently authenticate CI/signature QA. External release notes/Market or assembly qualify the same unchanged Entry/team/member commits as preview or production; changing product source requires a new release and new acceptance.

Only Mac arm64 is supported. Verify the current client from real platform observations, never source package/dev version. Before install: actual ToolCatalog Read page rendering, immutable ManageTeam fork, team-aware Delegate and ExportMedia. Generate smoke PDF using an explicit owned workspace output argument (never default publication output), extract text, actually Read page 1, ExportMedia the authorized page image into owned output and Read it back. Preserve complete actual tool receipts; directory presence or a supplied pass flag is insufficient.

After installation, use the read-only helper below with roots/commit/version from authorized current platform observations. Repeat `--member SLUG AUTHORIZED_ROOT` exactly once per manifest member. Absolute script paths are required; placeholders must be replaced with actual authorized values.

```text
python3 <absolute-skill>/scripts/check_local_install.py --entry-root <installed-entry-root> --expected-entry-commit <market-installed-entry-commit> --client-version <observed-client-version> --member <slug> <authorized-installed-root> ...
```

Exit 0 and `local_files_passed_tool_probes_required` only establish the reported local file/identity subset. Missing, changed, unsupported or unknown facts return blocked/nonzero. It does not run Read/ExportMedia, validate argument provenance, establish dependency runtime identity or approve rules. Relevant members must run their own locked formal helpers and report full real receipts; the entry must separately re-verify team/rules and actual tool probes before ready/handoff. No teammate environment borrowing or unpinned installs. File checks are bounded (4 MiB/file, 32 MiB total, 30-second cooperative deadline, each fixed read-only Git command at most 5 seconds). This is not an OS sandbox or a promise files cannot change afterward.

Manifest validator JSON status `passed` means structure/cross-fields only, with raw manifest/Schema hashes. Draft retains null platform identity/minimum, no team and no members; it permits diagnostics but zero network install. The existing CAS state helper and state Schema are unchanged. Ready means current local usability, not business or production acceptance.

## state_tool CLI (use verbatim)

```bash
# Exclusive init (requires real manifest path; records its real SHA-256)
python3 scripts/state_tool.py init <workspace-root> --manifest <path/to/release-manifest.json>

# Read and fully validate current state (semantic bad ⇒ exit code 2, scene preserved)
python3 scripts/state_tool.py read <workspace-root>

# CAS write (--expected-revision must match the current disk revision)
python3 scripts/state_tool.py write <workspace-root> <new-state.json> --expected-revision N
```

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | ok |
| 2 | Invalid state (syntactic or semantic) ⇒ recovery_required, scene preserved |
| 3 | Usage error |
| 4 | Lock busy: live holder ⇒ structured conflict; crashed/unknown holder ⇒ recovery_required, never force-delete or blindly retry |
| 5 | Revision conflict (CAS) |
| 6 | state_path_unresolved (location/permissions/symlink) |

## File map (relative to skill dir)

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Skill body (English) |
| `SKILL.zh-CN.md` | Skill body (Chinese) |
| `release-manifest.json` | Release manifest (current draft) |
| `schemas/release-manifest.schema.json` | Manifest Draft-07 Schema |
| `schemas/state.schema.json` | Private state Draft-07 Schema |
| `scripts/validate_manifest.py` | Manifest validator (stdlib) |
| `scripts/check_local_install.py` | Read-only local file/identity subset; not proof of tool execution or rule approval |
| `scripts/state_tool.py` | State tool: exclusive lock/CAS/full-structure validation/anti-escape |
| `scripts/generate_smoke_pdf.py` | Generate non-sensitive smoke PDF (stdlib; bitmap mark; mkstemp safe output) |
| `assets/smoke-tender-entry.pdf` | Smoke artifact |
| `docs/usage.md` | This file (English usage) |
| `docs/usage.zh-CN.md` | Chinese usage |
| `docs/recovery.md` | English recovery manual |
| `docs/recovery.zh-CN.md` | Chinese recovery manual |
| `LICENSE` | MIT license |
| `NOTICE` | Third-party notices |

## Safety constraints summary

- Scripts use only the Python standard library; no network calls, no local HTTP/LLM, no downloads, no execution of user-provided commands, no import of platform source.
- State stores only: package ID, manifest hash, revision, attemptId, real teamId/source commit/roster, validation summary/failure codes, handoff request coordinates. No credentials, no material content, no approval grant fields.
- State path rejects symlinks and path escapes; writes go through random exclusive temp file (mkstemp/O_EXCL) + `os.replace` atomic replace; the entire read-validate-compare-write sequence runs under a single cross-process exclusive lock.
- Draft manifest = zero install; no fakes (no fake URLs, no all-zero SHA, no HEAD-as-pinned-version, no guessed client version).
- URL validation is structural only (scheme/host/userinfo/whitespace); does not replicate platform DNS/SSRF engine; offline validation cannot prove the remote repo exists or was reviewed.

## Data handling

- **Local processing**: The skill scripts run entirely locally using only the Python standard library for file validation, state management, and manifest checks. No network calls, no external HTTP, no execution of user-provided commands.
- **Cloud model processing**: When the agent uses a cloud model (reading documents, analyzing images, generating responses), text and images you provide are sent to the model provider. This is governed by your compute configuration and provider terms — distinct from local script processing.
- **No unauthorized OCR/email/URL upload**: The entry does not install or use external OCR, email, or URL upload tools. PDF reading uses only the platform's built-in Read tool.
- **Not all processing stays local**: When submitting documents for review, the agent may send content to a cloud model for analysis. The entry does not and cannot claim otherwise.

## Fees and disclosures

- This skill is free and open-source (MIT license).
- Platform and cloud model service charges follow your compute configuration and provider pricing; they are not part of this skill.
- The entry is an orchestration tool to assist review — it does not replace human judgment.
- No authenticity verification, compliance guarantee, or winning guarantee is provided. Review conclusions are produced by team members; the entry re-verifies install and governance facts on each use but does not auto-re-review old professional conclusions — each new review request is handled by the team from scratch.

## Public contract binding (manifest v2, consumer candidate v3)

Each released member includes `delegationInputBinding` bound to that same member's immutable `repoCommit`. Lead requires `{"kind":"absent"}`; each of the four specialists requires `{"kind":"exact","value":<complete public delegation_input_contract>}`. The publisher derives the value only from that pinned public seed; no full private agent.json digest, model, approval preference or runtime path is published. The checker compares the pinned seed contract, manifest value and installed contract by JSON deep equality: object key order is irrelevant, array order matters, booleans differ from numbers. Lead and Entry must truly omit the field; null is not omission. Legitimate user model/approval preferences do not fail this contract comparison.

The existing fd-bound bounded read-only Git snapshot, Mac host constraint and local source verification remain unchanged. Exact contract matching does not run or authenticate the official platform subset validator and does not prove business execution. Publisher official acceptance and current real client capability probes remain required; an unavailable read-only official tool endpoint cannot be invented. Draft manifest platformRelease/minimumClientVersion/team stay null and members empty, with zero installation. No current public release/pin is claimed by this candidate. Preserve mismatches and block affected use, never restore an entire user's configuration or overwrite history to make the check pass.
