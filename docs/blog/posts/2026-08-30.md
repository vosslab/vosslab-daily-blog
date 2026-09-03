---
date: 2026-08-30
slug: making-chemical-bond-rendering-defects-measurable
generator_run: 20260902T021043Z-d0c7000466
evidence_manifest: evidence.json
editorial_projection: editorial_projection.json
---

# Making Chemical-Bond Rendering Defects Measurable

Today I spent most of my attention on [vosslab/ferrum-chemical-forge](https://github.com/vosslab/ferrum-chemical-forge), trying to make a renderer tell the truth about the ink it produces. A chemical drawing can be structurally valid and still be wrong in the way that matters to a reader: a bond can stop short, pass through a label, split unevenly, or leave a wedge looking disconnected. I wanted those failures to remain concrete enough that we could improve them without pretending they had disappeared.
<!-- evidence: ev-09c80b8011476164, ev-ab1feee2511e1d42 -->

<!-- more -->

## The renderer does not get to grade its own homework

The useful boundary is now outside the renderer’s own geometric reasoning. Rust test support emits enlarged draw-stream composites, structural core-glyph masks, and final bond footprints. A developer-only Python measurement library examines those raster artifacts for endpoint gaps, centerline drift, attachment, topology, clipping, and collisions. Instead of asking whether the renderer followed its internal rules, the measurement stack asks a plainer question: what pixels actually made it to the image?
<!-- evidence: ev-09c80b8011476164 -->

That sounds like an obvious distinction, but it changes the kind of confidence a green test can offer. The handoff is bounded and identity-checked: manifests, rasters, fixture identities, and policy data are cross-field validated and hash-bound. The V2 corpus contains twelve authoritative renderable fixtures and seven synthetic negatives. I removed the old V1 reader and its loose compatibility routes because this is not a general-purpose image script; it is a specific instrument with a specific claim about the image it measured.
<!-- evidence: ev-09c80b8011476164 -->

I particularly liked separating `raw_final_ink` from `presentation`. Native raster checks own pixel integrity, chemistry geometry, attachment, and clipping. Offscreen Qt capture owns the presentation evidence: fixed graph-authored viewport profiles and the actual consumer path. That keeps a badly framed screenshot from masquerading as a geometric defect, while also preventing a clean private raster from becoming enough evidence on its own.
<!-- evidence: ev-09c80b8011476164 -->

## Healthy instruments can still report bad news

The measurement stack now produces reports, overlays, and contact sheets per fixture, plus an atomic `run_summary.json` and a shared `measure_stack.batch` aggregate receipt. The current native receipt reports 26 strict-policy violations across seven renderable fixtures. Qt’s expected-red receipt continues to preserve detached endpoints and target-label overlaps instead of normalizing them into a passing result.
<!-- evidence: ev-09c80b8011476164 -->

That expected-red idea is the center of the day for me. The stack is healthy when it reproducibly captures, classifies, and explains a known set of failures. The renderer is not healthy merely because the scripts run. Keeping the strict gate red feels less satisfying than flipping a test green, but it gives the next correction an honest target. Green should mean that the chemical glyph is visually trustworthy, not that the test harness has become more accommodating.
<!-- evidence: ev-09c80b8011476164 -->

## Endpoint geometry got more specific

A large part of the work was learning that atom labels are not single rectangles. A decorated label may include isotope text or other non-core runs that ought to affect collision evidence, but not every decoration should block an incoming bond. The revised Rust-side clipping model uses the exact structural core glyph and only considers non-core Telex runs when they lie on the bond’s approach ray.
<!-- evidence: ev-09c80b8011476164 -->

The same specificity reached bond styles. Endpoint footprints now distinguish round endpoint ink, wedge-specific transverse width, and axial extensions. Wedge topology samples widths inside the final footprint rather than at fixed fractions of the atom-center span. Double and triple bonds calculate one endpoint clip across the complete parallel-lane footprint before emitting their symmetric lanes, rather than letting each lane make a contradictory claim about who owns the endpoint.
<!-- evidence: ev-09c80b8011476164 -->

Those changes reduced one native strict receipt from 22 findings to 15, eliminating opposed solid- and hashed-wedge topology and connection failures without changing the independent pixel policy. That is real movement, but the remaining seven strict-red fixtures are the useful part of the result. Parallel lanes, stereochemical and Haworth endpoints, detached connections, and label overlaps still need renderer-side work.
<!-- evidence: ev-09c80b8011476164 -->

## A promising local improvement failed the real replay

The best lesson came from two experiments that looked better in one lane and worse when asked to survive both. A raw convex-core support experiment raised the native receipt from 15 findings to 18. A dilated support lowered native findings to 10, but rebuilt Qt replay rose to 17, including full-label collisions. I removed both experiments and restored the 15-finding native receipt with the frozen expected-red Qt baseline.
<!-- evidence: ev-09c80b8011476164 -->

That is exactly why I wanted two independent lanes. It is easy to convince yourself that a private rendering correction is progress when the local diagnostic looks cleaner. The actual Qt consumer path supplied a counterargument: the apparent improvement had changed the visible behavior in a worse direction. The measurement design did its job by making that disagreement legible before it could become a claim of completion.
<!-- evidence: ev-09c80b8011476164 -->

The maintenance around the stack matters too. `GLYPH_BOND_MEASUREMENT.md` now records the evidence boundary, artifacts, statistics, thresholds, and developer lanes. Rust and Qt share a raster-manifest basename; the Rust gate discovers its repository through Git; slow artifact rebuilding remains a deliberate developer-oracle action rather than permanent pytest work. I also repaired the first-build bootstrap cycle and documented the hardened `lxml` parser boundary, while production CDML parsing remains owned by Rust and `xot`.
<!-- evidence: ev-09c80b8011476164 -->

The next problem is clear enough to be inviting. I do not need to prove that Ferrum can see defective bond rendering anymore. I need to find corrections that improve both the native final-ink evidence and the real Qt replay without weakening thresholds, changing fixture identity, or moving renderer responsibility into capture policy. That constraint is what makes the work feel worthwhile.

## Project coverage

- vosslab/ferrum-chemical-forge
- vosslab/starter-repo-template
- vosslab/syllabus
- vosslab/vosslab-podcast
