# Recovery Manual

This manual covers abnormal states in the first-use flow. **General rule: preserve the scene, never wipe and retry; never blindly re-dispatch; never fake a pass.**

## Phase codes → actions

### `state_path_unresolved` (state path unclear)

The private workspace cannot be located, permissions are unclear, path components are abnormal (symlinks, occupied by a file), or state_tool exit code 6.

**Action:** Stop all install-type actions. Re-confirm the registered directory via `ManageWorkDirs(action="list", scope="current")`; switching primary does not migrate state; a removed default dir is never replaced by an arbitrary project dir. Report abnormal dirs to the user and wait for human repair.

### `capability_blocked` (preflight failure)

Read lacks `pdf_mode=render`, ManageTeam lacks ref/expectedCommit, Delegate lacks teamId/handoff, or PDF smoke renderer dependency error.

**Action:** Write specific codes into `blockedCodes`; honestly tell the user to re-test once after client update. Never install external OCR, never substitute text-layer for visual verification, never repeatedly trigger a known dependency failure.

### `installing` with no receipt (in-flight unknown)

State has an `attemptId` with `installing` phase, but the fork receipt was lost or the session was interrupted.

**Action:** Set `recovery_required`. Use `ManageTeam(action="list")` read-only to check whether a matching team has appeared. Never issue `fork_team` again until a human confirms attribution.

### `recovery_required` (unknown origin / unrecorded install / crashed lock)

An unrecorded team install was found, source commit cannot be verified, or the state tool reports semantic corruption/crashed lock (exit code 2 or 4).

**Action:** Preserve the scene. Same name ≠ same origin: never adopt teams by name. A differing `members.lock.teamId` may be a redundant source-repo ID the platform normalizes on read — do not reject on that alone; but approval records must carry the real local teamId. Never delete/overwrite/rebuild a corrupt or unknown in-flight state/lock (init is exclusive and will refuse); a human may back up and rebuild afterwards.

### `upgrade_required` (manifest upgrade)

The skill manifest version is newer than the installed team's manifest version.

**Action:** Mark only; keep the old install working. Never auto pull/fork/overwrite user changes. Upgrade must be user-initiated after a real publication, redoing controlled install and rule approval.

### `waiting_rules_review` (awaiting rule approval)

The team is installed but rules have not been human-approved. Tool allowances ≠ rule approval.

**Action:** Guide the user through the TL-avatar team-settings path of the target team group; entry only read-only verifies existing records (real local teamId, LF/trim-normalized SHA-256, sorted-deduped roster). Scope-blocked reads stay blocked without changing permissions, scanning users, or HTTP bypasses. Never write/delete approval files, call approval HTTP, simulate confirmation, or flip ready on verbal claims. First import needs a real human confirmation source (user_confirmed/user_ui_write).

### `handoff_blocked` (handoff blocked)

Lead busy, refused, or acceptance unknown.

**Action:** Keep the request list; explain to the user. Never change target config or dispatch a second copy. First use `InspectRuns` to confirm the failed child run_id and verify it belongs to this session's dispatch. Then `Delegate(action="resume", run_id="<confirmed failed child run_id>", contextMode="continue")` continues only that specific failed run. Before resuming, use `InspectRuns` to check the latest and unique successor of the failed run. If a successor is running, wait for it; if the relationship is ambiguous, stop and report the uncertainty rather than resuming or dispatching again. Do not supply `message` unless a correction is needed; do not re-dispatch as a new async call. Stale reports never count as this run's completion.

## State tool exit codes

| Exit code | Action |
| --- | --- |
| 2 invalid state | recovery_required: preserve the scene, do not overwrite or re-init; human reviews and decides on backup/rebuild |
| 3 usage error | Fix the command and retry |
| 4 lock busy | **Live holder:** wait for it to finish; never kill the process or delete the lock. **Crashed/unknown holder:** recovery_required, human confirms before cleanup |
| 5 revision conflict (CAS) | Re-read the latest disk state, merge intent, and submit with the new expected-revision; never retry-overwrite |
| 6 path unresolved | See `state_path_unresolved` |

## Boundary reminders

- This skill publishes nothing. `status` may only become `released` after a real publication, with real HTTPS URL, real 40-hex ref/expectedCommit, real roster and asset hashes — missing any of these reverts to draft semantics.
- Offline structural validation cannot prove the remote repo exists or was reviewed; truthfulness is guaranteed by the publication receipt and subsequent install verification.
