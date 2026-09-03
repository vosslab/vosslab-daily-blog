---
date: 2026-08-15
slug: the-part-that-remembers
generator_run: 20260902T025927Z-02fec810b8
evidence_manifest: evidence.json
editorial_projection: editorial_projection.json
---

# The Part That Remembers

Today I finished a Python lifecycle cutover for [Peptidyle Learning Engine](https://github.com/vosslab/peptidyle-learning-engine), but the useful result was larger than replacing shell wrappers. The work became a local-system contract: explain how the stack starts, distinguish inspection from mutation, recover a failed dependency, and show that the workflow depending on it is useful again. <!-- evidence: ev-46a9beaa94a119b4, ev-73acfd09e77c425e -->

<!-- more -->

## Starting was never the interesting claim

The earlier lifecycle behavior was spread across shell entry points for launch, restart, and identity bootstrap. Focused Python controls now expose typed `start`, `status`, and read-only `validate` operations. I found that separation satisfying because a status or validation command should be able to tell the truth about a system without quietly repairing it first. <!-- evidence: ev-46a9beaa94a119b4, ev-73acfd09e77c425e -->

That distinction matters when a local environment is in an awkward state. A successful command or an existing process is weak evidence; the more useful question is whether a person can identify the condition, intervene at the broken dependency, and regain the learning workflow that depends on it. <!-- evidence: ev-73acfd09e77c425e -->

## Recovery had to cross a real boundary

The renderer made that standard concrete. The accepted work exercised renderer stop-and-restart alongside full WebWork RPC coverage, rather than accepting a running container as proof that recovery worked. Renderer OCI-ID normalization, seed-database environment fallback, removal of unsupported Compose `rm` behavior, restart readiness, and semantic renderer probing each addressed a seam where “running” could still conceal a broken workflow. <!-- evidence: ev-73acfd09e77c425e -->

Browser readiness and foreground handling belonged to the same lesson. A system is not meaningfully healthy merely because its components appear available; the handoff from dependency to API, and from automation to a usable browser path, has to carry the guarantee forward. <!-- evidence: ev-73acfd09e77c425e -->

## Shutdown became a statement about memory

The sharpest acceptance condition was the default shutdown boundary: zero containers and zero networks remain, while exactly `containers_ple_pgdata`, `containers_ple_miniodata`, and `containers_ple_identity_runtime` are retained. <!-- evidence: ev-73acfd09e77c425e -->

That gives the local system an intentional recovery point. Runtime machinery disappears instead of becoming debris, but PostgreSQL data, MinIO data, and identity runtime state survive for the next start. I like the clarity of that line: teardown is neither an accumulating pile of infrastructure nor a destructive reset of the state needed to resume meaningful work. <!-- evidence: ev-73acfd09e77c425e -->

The changed record also reaches through Rust data-access contracts; PostgreSQL and in-memory implementations; identity and invitation delivery; catalog, course, publication, and QTI paths; server composition and routing; fixtures; seed tooling; and conformance and live tests. The path list cannot establish the purpose of every edit, but it does show that lifecycle assumptions were distributed through the application rather than contained in a launcher. <!-- evidence: ev-f2aa4b4ad8633d9b -->

## The proof followed the handoffs

The final material-tree evidence recorded 4,881 passing pytest tests with no failures, skips, or warnings; all five `check_codebase.sh` stages; 260 Node tests; the full Rust check; and 202 ordinary Playwright tests. More important than the totals, the accepted coverage included schema-v2 walkthroughs across J11–J13, J1–J5, and J8; renderer recovery; full WebWork RPC; replica and restart durable replay; and a seven-lane aggregate. <!-- evidence: ev-73acfd09e77c425e -->

Chapter private provenance and a replica Question-ID manifest reinforced the same idea: durable replay needs evidence about what survives and what can be identified faithfully. Lifecycle confidence lives where guarantees commonly get lost—between restart and readiness, renderer and API, retained state and replay, or browser automation and foreground behavior. <!-- evidence: ev-73acfd09e77c425e -->

Three final reviews—the Python repository review, Podman security review, and walkthrough-acceptance review—returned `ACCEPT` with no P0–P3 findings. WP-PY-L1 is therefore an accepted direct-lifecycle and recovery contract, not merely a proposed architecture. <!-- evidence: ev-73acfd09e77c425e -->

M0 remains open, and WP-RC8 acceptance is next. The supplied record does not define that release-candidate condition further, so it will need to earn evidence of its own. For now, the system has a clearer place to start: it can shut down without forgetting itself, restart without hand-waving, and demonstrate that the dependent work is actually back. <!-- evidence: ev-46a9beaa94a119b4, ev-73acfd09e77c425e -->

## Project coverage

- [vosslab/peptidyle-learning-engine](https://github.com/vosslab/peptidyle-learning-engine) <!-- evidence: ev-73acfd09e77c425e -->
