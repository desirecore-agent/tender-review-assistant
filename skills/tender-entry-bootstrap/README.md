# Tender Review Assistant — Entry Bootstrap Skill

A first-use bootstrap skill for the DesireCore tender-review-assistant agent.

**What it does:** When a new user installs this agent from the marketplace, this skill verifies install conditions, performs one controlled team install (when a real team has been published), waits for human rule approval, and hands off the real request to the lead reviewer.

**What it does NOT do:** It does not perform professional tender review itself, and it does not guarantee compliance, regulatory adherence, or winning any bid.

## Key concepts

| Term | What it means |
| --- | --- |
| **Entry install** | Installing this agent from the marketplace. This only gives you the entry point — no review team is installed automatically. |
| **Team install** | A separate, explicit step: one controlled `fork_team` call with a pinned commit from a real published team. Only happens when the manifest is `released` and preflight passes. |
| **Rule approval** | After the team is installed, a human must review and confirm the team's rules via the DesireCore GUI before any review can begin. Tool allowances ≠ rule approval. |
| **Ready** | All of the above have been verified in the current session. This is re-verified on every use, not cached. |

## Installation

Install the `tender-review-assistant` agent from the DesireCore marketplace. The entry bootstrap skill comes bundled.

## Release and local capability boundary

`released` means published immutable source, not production qualification. Publisher QA is checked by private assembly; current Entry checks the publisher declaration bound to its actual installed commit. It does not independently authenticate CI/signature QA. External release notes/Market or assembly qualify the same unchanged Entry/team/member commits as preview or production; changing product source requires a new release and new acceptance.

Only Mac arm64 is supported. Verify the current client from real platform observations, never source package/dev version. Before install: actual ToolCatalog Read page rendering, immutable ManageTeam fork, team-aware Delegate and ExportMedia. Generate smoke PDF using an explicit owned workspace output argument (never default publication output), extract text, actually Read page 1, ExportMedia the authorized page image into owned output and Read it back. Preserve complete actual tool receipts; directory presence or a supplied pass flag is insufficient.

After installation, use the read-only helper below with roots/commit/version from authorized current platform observations. Repeat `--member SLUG AUTHORIZED_ROOT` exactly once per manifest member. Absolute script paths are required; placeholders must be replaced with actual authorized values.

```text
python3 <absolute-skill>/scripts/check_local_install.py --entry-root <installed-entry-root> --expected-entry-commit <market-installed-entry-commit> --client-version <observed-client-version> --member <slug> <authorized-installed-root> ...
```

Exit 0 and `local_files_passed_tool_probes_required` only establish the reported local file/identity subset. Missing, changed, unsupported or unknown facts return blocked/nonzero. It does not run Read/ExportMedia, validate argument provenance, establish dependency runtime identity or approve rules. Relevant members must run their own locked formal helpers and report full real receipts; the entry must separately re-verify team/rules and actual tool probes before ready/handoff. No teammate environment borrowing or unpinned installs. File checks are bounded (4 MiB/file, 32 MiB total, 30-second cooperative deadline, each fixed read-only Git command at most 5 seconds). This is not an OS sandbox or a promise files cannot change afterward.

Manifest validator JSON status `passed` means structure/cross-fields only, with raw manifest/Schema hashes. Draft retains null platform identity/minimum, no team and no members; it permits diagnostics but zero network install. The existing CAS state helper and state Schema are unchanged. Ready means current local usability, not business or production acceptance.

## Team rules approval path

After a team is installed, the entry instructs the user to:

1. Open the lead reviewer session from the sidebar.
2. Use the lead's avatar (TL) entry to open the **target team's** settings group (not the old MoreMenu first team).
3. Verify the team name and real teamId in settings.
4. Review and confirm the rules.

The entry only reads existing platform records. It never writes, deletes, or simulates approval files.

## Failure recovery

- **Corrupt state** is preserved on disk — never wiped or re-initialized. The user decides how to recover.
- **Lock contention** returns a structured error (exit code 4) — the lock is never force-deleted.
- **Duplicate start** will not re-install a team. The existing state is re-verified; `recovery_required` is returned if the state is inconsistent.
- **Lost fork receipt** enters `recovery_required` — the entry never blindly re-forks.

## Data handling

- **Local processing:** The skill's Python scripts run entirely locally using the Python standard library. They perform file validation, state management, and manifest checks. No network calls, no HTTP to external services, no command execution from user input.
- **Cloud model processing:** When the DesireCore agent uses a cloud model (e.g., for reading documents, analyzing images, or generating responses), the text and images you provide to the agent may be sent to that model provider for processing. The user must have the right to share the corresponding materials with the chosen model service and must provide the necessary authorization to do so. This does not authorize sending materials to any other service. Processing is governed by your DesireCore compute configuration and the model provider's terms — it is not the same as local script processing.
- **No unauthorized OCR:** The entry does not install or use any external OCR, email, or URL upload tools. PDF reading uses only the DesireCore platform's built-in Read tool.
- **Not all processing stays local:** The agent's Python scripts are local, but document review may involve sending content to a cloud model you have configured. The entry never promises or implies that all processing stays on your local machine — that is an inaccurate claim we explicitly disavow.

## Scope

This skill provides an **entry point and orchestration layer** only. It:

- Verifies conditions and installs the review team.
- Waits for human rule approval.
- Hands off requests to the lead reviewer.

**State and data boundaries:**
- The entry's private state is fixed at `<workspace>/.desirecore/tender-entry-bootstrap/state.json` (located via `ManageWorkDirs` into the agent's registered private workspace; switching primary does not migrate state). The tool's state file and user materials are separate concerns managed under different scopes — users are not restricted to choosing only the state directory, and the state directory is not assumed to be the exclusive location for materials.

It does **not**:

- Perform any professional review conclusions (eligibility, pricing, image evidence).
- Guarantee compliance, bid-winning, or review coverage.
- Modify other agents, teams, or platform approval records.

## Fees

- This skill itself is free and open-source (MIT license).
- Using the DesireCore platform and cloud model services may incur charges according to your compute configuration and provider pricing. These charges are for the platform and model services, not for this skill.

## Pending items

The following require a real published team and platform updates before they can be tested:

1. Real `fork_team` install with receipt verification.
2. Same-name team isolation, upgrade retention, lost-receipt recovery.
3. Full GUI rule approval flow.
4. Real `Delegate(handoff=true)` with target busy/rejected/unknown handling.
5. Released manifest backfill and verification.

**This skill does not claim production readiness until all of the above have been verified with real published assets.**

## License

All original code and documentation in this skill directory are released under the [MIT License](LICENSE). This license applies only to original work by the Tender Review contributors. It does not apply to third-party dependencies, the Python runtime, the DesireCore platform, or any model services — those are provided under their own licenses and terms.


Local identity helper security limits: source paths are opened component by component with NOFOLLOW and retained directory descriptors. Git operates only on a bounded temporary object/ref snapshot, without repository config, hooks, filters, index or alternates. Temporary files are removed on exit; installed sources are never modified. Linked worktree gitdir files and symlinked/external object stores fail closed. Raw blob comparison rejects checkout byte transformations, including CRLF conversion. This is a local file check, not publisher, CI, runtime or production certification.

## Public contract binding (manifest v2, consumer candidate v3)

Each released member includes `delegationInputBinding` bound to that same member's immutable `repoCommit`. Lead requires `{"kind":"absent"}`; each of the four specialists requires `{"kind":"exact","value":<complete public delegation_input_contract>}`. The publisher derives the value only from that pinned public seed; no full private agent.json digest, model, approval preference or runtime path is published. The checker compares the pinned seed contract, manifest value and installed contract by JSON deep equality: object key order is irrelevant, array order matters, booleans differ from numbers. Lead and Entry must truly omit the field; null is not omission. Legitimate user model/approval preferences do not fail this contract comparison.

The existing fd-bound bounded read-only Git snapshot, Mac host constraint and local source verification remain unchanged. Exact contract matching does not run or authenticate the official platform subset validator and does not prove business execution. Publisher official acceptance and current real client capability probes remain required; an unavailable read-only official tool endpoint cannot be invented. Draft manifest platformRelease/minimumClientVersion/team stay null and members empty, with zero installation. No current public release/pin is claimed by this candidate. Preserve mismatches and block affected use, never restore an entire user's configuration or overwrite history to make the check pass.
