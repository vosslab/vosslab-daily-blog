---
date: 2026-08-28
slug: one-date-one-drawing-one-source-of-truth
generator_run: 20260831T023101Z-00f0b92468
evidence_manifest: evidence.json
editorial_projection: editorial_projection.json
---

# One Date, One Drawing, One Source of Truth

Today kept returning me to the same satisfying constraint: a system becomes easier to trust when it gives one layer the authority to decide a thing, then makes everyone else carry that decision faithfully instead of re-deriving it. That idea showed up in a chemical renderer, a grading recovery path, a syllabus table, and even the machinery that may someday publish a post like this one. <!-- evidence: ev-5e62b41aba794b5c, ev-74d2be88c974b8b2, ev-f2a55e8e353e5190, ev-69e3ed92696e7bc7 -->

<!-- more -->

## The line is not the bond

Most of my attention went to [vosslab/ferrum-chemical-forge](https://github.com/vosslab/ferrum-chemical-forge), where I was closing a boundary between Rust’s molecular depiction work and Qt’s visible rendering. Chemical drawing has a deceptively hard failure mode: two atoms can be structurally connected, yet the visible bond can still run into a label, collide with an isotope decoration, or stop at a place that makes the molecule look wrong. The question is not merely whether a bond exists. It is which part of the system gets to say what that bond should look like. <!-- evidence: ev-5e62b41aba794b5c -->

I made that distinction explicit with `BondAttachmentAxisV1`. Rust derives a center-to-center structural axis before clipping and sends it through PyO3 for Qt to validate. Crucially, Qt does not paint or hit-test that axis. It is evidence of attachment, not a shortcut around the actual visible geometry. The final drawn line still has to clear the full ink of the endpoint labels. I like that separation because it turns a fuzzy visual rule into two honest facts: these atoms are connected, and this ink must not overlap that ink. <!-- evidence: ev-5e62b41aba794b5c -->

The rest of the renderer followed that decision. Generic operation bags gave way to frozen V4/V2 typed DTOs: one closed atom, compact-group, or bond payload per batch. Atom labels carry Rust-issued Telex bounds, core-run identity, paint order, and validated positive `bond_ink_clearance`. Qt replays those typed facts and validates them; it no longer has to act as a second depiction engine trying to infer chemical meaning from an open-ended stream of drawing instructions. <!-- evidence: ev-5e62b41aba794b5c -->

That change reached further than transport code. Attached compact-group pose admission and final normal-single bond clipping now share the renderer-issued, font-derived clearance policy. A proposed edit that cannot produce an admissible depiction is no longer just visually unfortunate after the fact; ordinary authoring does not admit it. I enjoyed watching that rule expose fixtures and generated geometry that were structurally plausible but inherently unrenderable at Ferrum’s native scale. <!-- evidence: ev-5e62b41aba794b5c -->

The test shape mattered as much as the code shape. I added the twelve-case `atom_label_bond_alignment_cases_v1` corpus at the document-to-V4 observation seam, where it can prove emitted label and bond content, operation ordering, isotope core-run behavior, and a target-specific refusal without pretending that pixel snapshots are the right proof of everything. Installed Qt tests and real-window E2E work then exercise the actual consumer. The local aggregate recorded 8,297 hygiene tests, all registered CLI and Qt E2E tests, 299 installed PyO3 tests, and 437 Qt tests passing. <!-- evidence: ev-5e62b41aba794b5c -->

The machine contract is clearer now, but that is not the same as declaring victory for a human user. Dense labels, attached compact groups, selection behavior, and accessibility workflows still deserve direct desktop review. I have more confidence that the renderer is saying one coherent thing; the next question is whether that coherence is as obvious to someone using it as it is to the code enforcing it.

## Recovery should not create a new authority

In [vosslab/peptidyle-learning-engine](https://github.com/vosslab/peptidyle-learning-engine), I was interested in a different boundary with the same underlying shape: a learner’s answer can be durable enough to recover from failure without becoming routine operational data. The accepted `WP-INST-G1` path lets a successful submission enter `acceptedPending`, provides the learner a receipt and status, and allows later processing to resume from the immutable server-private submission. Recovery is status-only; it does not ask the learner to submit again or hand broad visibility of their work to the browser. <!-- evidence: ev-74d2be88c974b8b2 -->

The proof I cared about was not a retry endpoint by itself. The production browser journey submits once, reaches `acceptedPending`, creates deterministic Instructor attention, and lets one Instructor retry lead to completed learner feedback without a second learner answer POST. Replay returns the original receipt rather than manufacturing a second authority over the response. That is the kind of detail that makes recovery feel like recovery rather than a disguised resubmission workflow. <!-- evidence: ev-74d2be88c974b8b2 -->

The Instructor interface was narrowed to match the backend claim. It keeps the question title as a heading, exposes a stable copyable Question ID with accessible success feedback and a manual-copy fallback, and binds retry to that exact title and ID. The Instructor Student view remains answer-free when that role has no reason to see the response. Connected PostgreSQL/RLS checks include a five-UUID retry-V2 denial with SQLSTATE `42501`, alongside checks for receipt category, actor provenance, and worker exclusivity. <!-- evidence: ev-74d2be88c974b8b2 -->

I also spent time making the evidence path less magical. The live-demo scripts now own a fixed Python 3.12 `.venv`, test and runtime requirements are separated, and the virtual environment is excluded from frontend-tool traversal after an aggregate gate found ESLint walking pip-vendored JavaScript. Reproducibility is not glamorous work, but it is what lets a privacy or recovery claim survive past the moment when it was first demonstrated. <!-- evidence: ev-74d2be88c974b8b2 -->

The next planned slice, `WP-INST-G2`, is deliberately harder: a roster-first calculated Gradebook and one explicit audited Student-work inspection read. It is not delivered capability. I want to find out whether useful Instructor workflows can remain exceptional and accountable enough that they do not quietly erase the narrow privacy boundary that made G1 worthwhile. <!-- evidence: ev-74d2be88c974b8b2 -->

## A table is also a contract

The day also had a quieter version of the same lesson in [vosslab/syllabus](https://github.com/vosslab/syllabus). A grading table looks like a modest presentation detail until it appears independently in a website, PDF, and DOCX file. Then every manually copied total, percentage, assessment label, and policy sentence becomes a small chance to tell students three slightly different stories. <!-- evidence: ev-f2a55e8e353e5190 -->

I moved confirmed course point plans into manifest-owned YAML lists of assessment names and integer points. The publication paths derive totals and approximate shares from that source instead of carrying table arithmetic in Markdown. I also made the display rule exact: shares are rounded half-up to one decimal place, trailing `.0` disappears, Genetics renders 100 out of 424 as `23.6%`, and the Total row remains exactly `100%` rather than inheriting display-rounding noise. <!-- evidence: ev-f2a55e8e353e5190 -->

The feature I particularly enjoyed was almost embarrassingly simple: every plan now has a blank **Your points** column. Students can use the document they received to calculate their own standing. The Total row is bold across formats, with matching visual treatment in website and PDF output and preserved emphasis in DOCX. One compact data model did not force identical rendering; it gave each output the same policy facts and let each format present them clearly. <!-- evidence: ev-f2a55e8e353e5190 -->

The cleanup spread into the surrounding language. Live schedules and the shared format policy again state unconditionally that syllabi may change at any time. Obsolete or overly specific terminology was removed, including wording that assumed assignments happen outside class or depend on Blackboard Ultra. The release evidence included 1,165 fast tests, live Google Sheets export, PDF/DOCX generation, a strict MkDocs build, cross-format parity checks, and a production Playwright accessibility audit. <!-- evidence: ev-f2a55e8e353e5190 -->

Biostatistics remains intentionally unfinished: there is a non-live point-plan draft, but the Fall 2026 syllabus stays unchanged until instructor confirmation. That restraint is part of the point. Software can make a confirmed policy easy to publish consistently; it should not quietly decide the policy first. <!-- evidence: ev-f2a55e8e353e5190 -->

## The blog is learning to wait

Finally, [vosslab/vosslab-podcast](https://github.com/vosslab/vosslab-podcast) spent the day making its own publication authority more explicit. The production contract now treats `report_date` as the one identity of a publication and holds the current validated bundle in one stable `publication/` directory. A bundle hash remains integrity evidence, not a competing identity. Existing dates also have a concrete rule: unattended work leaves a coherent publication alone without model work, while interactive replacement requires the exact response `y` and runs under one per-date lock. <!-- evidence: ev-69e3ed92696e7bc7 -->

The more interesting outcome is the maker-voice experiment. I added a sealed capture artifact, a separate attestation schema and command, paired A/B and B/A comparisons, and strict acceptance requirements. But the experimental `v4-maker` policy cannot publish, acquire the production lock, refresh mirrors, route a model, write a bundle, import itself into the publisher, alter the schedule, or activate itself. Production remains active policy v3, enforced by both orchestrator and publisher. <!-- evidence: ev-69e3ed92696e7bc7 -->

There is real satisfaction in building a system that can say “not yet” without ambiguity. The experiment can capture evidence, calibrate, and produce a deterministic attestation; it cannot treat a promising result as permission to become public. The evidence is still incomplete: an authorized no-content Hermes smoke succeeded, but a full project-evidence capture stopped at the external-action gate. There are no live rubric scores, no winning arm, no v4 activation, and no experimental publication. <!-- evidence: ev-69e3ed92696e7bc7 -->

That may be the day’s clearest lesson. The useful boundary is not the one that makes action impossible. It is the one that makes every action legible: a renderer may validate but not redraw meaning, recovery may resume but not expose answers, a manifest may publish a policy but not invent it, and an experiment may gather evidence without calling itself ready.

## Project coverage

- vosslab/ferrum-chemical-forge
- vosslab/peptidyle-learning-engine
- vosslab/syllabus
- vosslab/vosslab-podcast
