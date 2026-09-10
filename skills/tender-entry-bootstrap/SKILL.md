---
id: tender-entry-bootstrap
name: tender-entry-bootstrap
version: 0.1.0
description: First-use bootstrap for the tender review entry agent - verify install conditions, perform one controlled team install, wait for human rule approval, then hand off the real request to the lead reviewer.
triggers:
  - tender review first use / bootstrap
  - install review team
  - review preparation / environment check
scope: agent
---

## L0

This skill only performs entry guidance: verify → controlled install → wait for rule approval → hand off to the lead reviewer. The entry agent itself never does professional tender review and never guarantees compliance or winning the bid.

## L1 (Operating flow)

### 0. Ground facts

- All paths in this skill are relative to the skill directory (`schemas/`, `scripts/`, `assets/`, `docs/`). The single absolute-path exception is the private state file (§1), which MUST stay in the entry agent's own registered private workspace.
- **Workspace-bound I/O**: Any temporary files, candidate state files, command output captures, and test artifacts created during skill execution MUST reside inside the current agent's registered private workspace (obtained via `ManageWorkDirs(action="list", scope="current")`). Writing to system `/tmp`, the skill's own publication directory, user tender folders, or any path outside the private workspace is forbidden. Use unique filenames or subdirectories within the workspace to avoid collisions.
- **Script invocation**: All calls to skill scripts (`validate_manifest.py`, `state_tool.py`, `generate_smoke_pdf.py`) MUST use the real absolute path resolved from the skill directory — never relative paths that depend on cwd.
- **Command audit**: Every command execution must capture and record the complete stdout, stderr, and real exit code, including failures. Exit code 0 must never be assumed or substituted when a command was not actually run or its output was not captured. An omitted or lost exit code is recorded as `exit_code_not_captured`, never as 0.

### 1. Locate private state

- Use `ManageWorkDirs(action="list", scope="current")` to obtain the registered private workspace; the user ID comes from the platform-injected identity — never guessed, never scanning other users' directories.
- The state file is fixed at `<workspace>/.desirecore/tender-entry-bootstrap/state.json`. It does NOT follow the current cwd and must NOT live in the publication dir or any user tender folder.
- Unresolved location/permissions → record `state_path_unresolved` and stop install-type actions.
- All state I/O goes through `scripts/state_tool.py` (argparse subcommands: `init <workspace> --manifest <manifest-path>` / `read <workspace>` / `write <workspace> <new-state-file> --expected-revision N`). A cross-process exclusive lock covers the WHOLE sequence "read current state → full structural validation → revision compare → candidate validation + consistency check → same-directory atomic write". Exit codes: 0 ok; 2 invalid state (syntactic OR semantic; scene preserved); 3 usage error; 4 lock busy (another holder; structured conflict); 5 revision conflict; 6 path unresolved. Symlinks and path escapes are refused; init is exclusive; a crashed lock or unknown in-flight attempt is `recovery_required` — never blindly delete the lock, never blindly retry, never re-fork.
- **Never store** in state: credentials, user material bodies, or any "approval granted" flag. Approval is re-verified read-only on every use; never cached.

### 2. Release binding and local preflight (never skip)

- The installed immutable Entry commit and actual Market installation source carry the publisher declaration. Obtain their real identities from authorized platform installation records; never infer trust from this manifest itself, a same-name Agent, or a caller-supplied hash. Missing source provenance blocks install/use. The manifest validator checks structure/cross-fields only; it does not authenticate CI, signatures or publisher QA. Publisher release QA is independently checked during assembly, not re-run by newcomers.
- Run the exact installed `scripts/validate_manifest.py` against the installed manifest. Its JSON output must have `status=passed`, matching raw manifest and Schema hashes and real exit 0. Draft remains zero install with null platform identity/minimum. Released does not mean production-ready; preview/production qualification is external and bound to the unchanged release commits.
- Verify the current client version from actual platform facts against the non-null released minimum. Only Mac arm64 is supported; unknown/other hosts report unsupported and stop locally. Never use a development source version as an issued client release.
- Before installation, use the actual ToolCatalog to verify Read rendered pages, ManageTeam immutable `ref`/`expectedCommit`, Delegate team-aware handoff and ExportMedia. Use the exact current parameter Schema, not historical example syntax. Missing capability blocks the affected use; do not invent arguments or downgrade to text-only verification.
- Run a real PDF/image smoke in the entry's own private workspace: generate the existing public synthetic PDF with the documented output argument; extract text, then actually Read page 1 as an image, confirming the image-only mark. Actually ExportMedia the returned authorized media pointer into an owned private output, and Read that exported image. Preserve exact request, full response/stdout/stderr/exit as applicable, current turn/run and output identities. ToolCatalog presence or a JSON `passed` assertion is not an executed probe. No external OCR, global installs or developer security audit is needed.
- After the controlled team installation, call `scripts/check_local_install.py` with Entry root and expected Entry commit from the actual installation receipt, current observed client version, and each exact member root obtained through authorized ManageTeam/ManageAgent facts. It checks current Mac host, committed Entry Skill changes, member source commits, immutable UUID/version and every criticalAsset hash. It is read-only and never returns ready: `local_files_passed_tool_probes_required` is only the file/identity subset. All `notVerified` items remain outside its proof. Do not feed private raw configs into reports.
- Each member must itself call `ManageWorkDirs(action="list", scope="current")` to discover its registered private workspace. Entry's own list is not a substitute. Team shared cwd is not the private runtime location; never traverse another Agent's user directories or derive a venv from a guessed relative path. The runtime is Agent-managed, not necessarily in the platform Hatch/Volta list. The member reports interpreter identity/version, environment prefix, lock hash and required real helper smoke in a non-secret receipt at the authorized current initialization output, with current producer/run/task identity. Entry reads only the expressly authorized delivered receipt; inaccessible/missing/stale receipt blocks the function, never fallback to an old private run. Do not put runtime paths, private receipts or user identities into the public manifest.
- Before professional use, each relevant member verifies its OWN locked runtime and executes its required installed formal helper on authorized non-sensitive preflight input. Evidence checks its locked validator and applicable Lead TaskSpec checker; Visual checks its locked image helper and applicable ROI coverage helper; Requirements and Commercial use their required installed formal routines. Use current installed Skill/lock/Schema, exact versions and full actual receipts. Do not borrow another member's environment, install an unpinned replacement, or invent a surrogate script. The entry collects receipts without rewriting member output. Missing/unknown/failed runtime or helper evidence blocks the affected function.
- Re-verify current install/team/asset hashes and actual human rule confirmation before every handoff; retain existing CAS/state phases and blockedCodes. `ready` records current local usability only, never business correctness, publisher QA authentication or production acceptance. Do not store permission-grant flags. Any manifest/source change is an upgrade, not permission to silently refresh hashes or fork again.

### 3. Manifest verification

- `python3 scripts/validate_manifest.py release-manifest.json` must pass first.
- `status="draft"` (the current true state) ⇒ **zero fork / zero network install**: only capability diagnostics and writing blockers to state are allowed; no fork_team/remote install actions.
- `status="released"` AND the pre-install source/client/tool checks in §2 passed ⇒ enter §4. Post-install file/runtime/helper/rules checks occur only after that installation and must pass before §6 handoff; they are not prerequisites for creating the team. A manifest upgrade only sets `upgrade_required`, keeps the old install, and never auto pull/fork/overwrites user changes.

### 4. Controlled install (released only)

1. First check state: if a teamId for this exact manifest exists, verify-and-reuse: `ManageTeam(get)` for roster/versions/real dirs, read-only check of source commit history and critical asset hashes, `ManageAgent(get)` per member. **Never adopt a same-name team by name alone** — only the real teamId recorded in state and fork receipts count.
2. New install only without a record: persist `attemptId` first (phase=`installing`), then call `ManageTeam(action="fork_team", url=<manifest>, ref=<40-hex SHA>, expectedCommit=<same 40-hex SHA>, installMembers=true)` exactly once, and immediately persist the returned teamId/resolvedCommit.
3. Tool success but failed members/warnings ⇒ `partial`; record honestly, never claim full readiness.
4. Lost receipt / unknown origin / unknown pre-existing install ⇒ `recovery_required`; preserve the scene, never blindly re-fork; never invent tools like `install_members`/`approve`.

### 5. Wait for rule approval

- After fork, set `waiting_rules_review`. **All tool calls being allowed ≠ rules approved.**
- Instruct the user: enter the lead reviewer's session from the sidebar, use the lead's avatar TL entry to open the team settings of **the target team group** (with multiple teams, never use the old MoreMenu's first team); verify team name + real teamId there, review and confirm the rules; the platform will later provide an entry that opens settings and returns the team ID. Then return here.
- The entry may only READ existing platform team-approvals records and `rules.md` within authorized scope, checking teamId, normalized (LF / trimmed line-ends) content SHA-256, and roster (sorted, deduped). Note: `members.lock.teamId` may be a redundant source-repo ID; the platform normalizes it to the local ID on read — never reject on that difference alone; but approval records must carry the real local teamId. Missing/mismatch/read-scope-blocked ⇒ stay in `waiting_rules_review` and remain blocked; verbal confirmation can never flip to ready; never change permissions, scan other users' dirs, or bypass via local HTTP.
- Never write/delete approval files, never call approval HTTP endpoints, never simulate user confirmation. Re-verify on every use; never cache "approved" permanently. First import of rules requires a real human confirmation source (user_confirmed/user_ui_write); team_imported with roster only never counts as rules reviewed.

### 6. Hand off to the lead

- Once `ready`, build only a **private request list**: original request, authorized file absolute paths/media pointers, hashes, missing materials, read-only constraints on originals. Store coordinates only, never material bodies.
- Default: `Delegate(target=<lead slug from manifest>, handoff=true, teamId=<verified>, task=<faithful first-person restatement of the original request>, context=<material coordinates and constraints>)`; the platform switches the user to the lead's session and the entry stops duplicating review work.
- Target busy/refused/acceptance unknown ⇒ `handoff_blocked`: keep the request, explain; never change target config, never dispatch a second copy.
- Discriminate by this run's requestId/correlationId/childRunId; stale reports or a bare Delegate success never count as this run's completion.

## L2 (Boundaries and counter-rules)

- **Entry duty ceiling**: only install-condition verification, controlled install orchestration, approval waiting, and hand-off. All professional review conclusions belong to the team members.
- **Never promise**: compliance, winning the bid, or review coverage.
- **Forbidden**: creating new agents; modifying the lead/member configs; publishing the team or skill (release status is changed only through the separately authorized and reviewed publication workflow); calling non-existent tools; fake URL/all-zero SHA/HEAD-as-pinned-version; adopting teams by name; blindly re-forking; deleting or bypassing approvals.
- See `docs/usage.md` and `docs/recovery.md` for usage and recovery details.

## Public contract binding (manifest v2, consumer candidate v3)

Each released member includes `delegationInputBinding` bound to that same member's immutable `repoCommit`. Lead requires `{"kind":"absent"}`; each of the four specialists requires `{"kind":"exact","value":<complete public delegation_input_contract>}`. The publisher derives the value only from that pinned public seed; no full private agent.json digest, model, approval preference or runtime path is published. The checker compares the pinned seed contract, manifest value and installed contract by JSON deep equality: object key order is irrelevant, array order matters, booleans differ from numbers. Lead and Entry must truly omit the field; null is not omission. Legitimate user model/approval preferences do not fail this contract comparison.

The existing fd-bound bounded read-only Git snapshot, Mac host constraint and local source verification remain unchanged. Exact contract matching does not run or authenticate the official platform subset validator and does not prove business execution. Publisher official acceptance and current real client capability probes remain required; an unavailable read-only official tool endpoint cannot be invented. Draft manifest platformRelease/minimumClientVersion/team stay null and members empty, with zero installation. No current public release/pin is claimed by this candidate. Preserve mismatches and block affected use, never restore an entire user's configuration or overwrite history to make the check pass.
