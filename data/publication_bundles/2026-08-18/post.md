---
date: 2026-08-18
slug: a-spread-is-not-yet-a-book
generator_run: 20260901T155433Z-7756419335
evidence_manifest: evidence.json
editorial_projection: editorial_projection.json
---

# A Spread Is Not Yet a Book

The day’s clearest lesson arrived through a scanned book: an artifact can look useful before it has earned the claim we want to make for it. A landscape PDF spread may contain two facing pages, but generic OCR sees one wide image. Pulling words from that image is not the same thing as recovering the reading order, structure, and reference value of a book.
<!-- evidence: ev-c64f2ec7dbe5afad -->

<!-- more -->

## Splitting the source from the document

I moved [book-to-markdown](https://github.com/vosslab/book-to-markdown) into a standalone repository and gave it a staged shape: extraction, cleanup, validation, auditing, and archiving. The target is one clean, page-free Markdown document, not merely a folder of text extracted from PDF pages. That distinction gives problems an honest place to belong: source access, damaged structure, and failed delivery checks are related, but they are not the same failure.
<!-- evidence: ev-c64f2ec7dbe5afad, ev-9dc90ec3afaf41cf -->

The new spread-scan path makes the difference concrete. `extract/pdf_ocr_spread_halves.py` and `pdf_extract/spread_ocr.py` split a scanned two-page landscape spread before OCR, producing halves that can be assembled in the sequence a reader expects. The workers also set `OMP_THREAD_LIMIT=1`, because parallel Tesseract jobs can otherwise multiply their own OpenMP thread load and spend time competing for CPU instead of making useful progress.
<!-- evidence: ev-c64f2ec7dbe5afad -->

The more consequential work comes after recognition. `cleanup/assemble_ocr_halves.py` treats OCR output as page-local evidence rather than finished prose: it removes gutter noise, running heads, and page numbers; detects chapters; joins paragraphs across page boundaries; and rebuilds front matter and contents. Its JSON configuration carries edition-specific facts such as chapter keys, recurring heads, title fragments, and front-matter mappings, while the code owns the reusable reconstruction mechanics.
<!-- evidence: ev-c64f2ec7dbe5afad -->

That boundary is satisfying because it avoids two misleading promises. Hard-coding one title’s typographic quirks would make a one-off success look general. Pretending every edition can be understood with no contextual input would conceal where the tool needs help. Configuration makes those local facts explicit without giving up on a repeatable conversion process.
<!-- evidence: ev-c64f2ec7dbe5afad -->

## More processing was less faithful

An earlier conversion defect showed why the extractor choice needs to stay visible. The old structured route used `pymupdf4llm.to_markdown()` with OCR enabled even for pages that already had a clean embedded text layer, then merged the OCR and text-layer streams. On one measured page, that produced 2,351 words and 378 duplicate pairs; replacing it with `fitz.get_text()` produced 1,231 words and no duplicate pairs.
<!-- evidence: ev-9dc90ec3afaf41cf -->

The repair split the former 1,151-line `pdf_to_markdown.py` into two extractors backed by a shared `pdf_extract` package: one reads an existing text layer through `fitz.get_text()`, and the other OCRs image-only scans with `get_textpage_ocr()`. Shared cleanup, scoring, and reporting remain shared, but OCR no longer presents itself as a harmless enhancement to text that was already clean.
<!-- evidence: ev-9dc90ec3afaf41cf -->

That is the kind of simplification worth trusting: it was not aesthetic cleanup, but the removal of a more elaborate path that had materially doubled the source. The conversion tools now have a clearer way to say what they did, which source condition they responded to, and what still needs inspection.
<!-- evidence: ev-9dc90ec3afaf41cf -->

The instructional boundary changed with the implementation. `vosslab-skills` now keeps `SKILL.md` as a focused workflow shell with tracked procedural references, while the standalone repository owns conversion, validation, auditing, dependencies, and tests. The remaining proof is practical: someone unfamiliar with the retired layout still needs to be able to begin at the skill, locate the tools, select the right path, verify the result, and complete a conversion.
<!-- evidence: ev-9dc90ec3afaf41cf -->

## Screenshots that can disagree with us

The same concern shaped [Peptidyle Learning Engine](https://github.com/vosslab/peptidyle-learning-engine). A committed screenshot can be persuasive while failing to explain which route it represents, which role saw it, what pipeline produced it, why it required live capture, or whether it still reflects the browser code. The new `tests/playwright/ui_corpus_manifest.ts` makes those claims explicit for 24 governed artifacts: surface, route, role, owning pipeline, live-capture rationale, and evidence purpose. Both capture runners now consume that one declaration rather than maintaining separate filename lists.
<!-- evidence: ev-4f8eca4156d50ba0 -->

The provenance and verification tools deliberately avoid treating freshness as a binary certificate. Because large browser changes tend to land together in this repository, narrowing the source path did not create a more meaningful ownership boundary. The tooling instead reports staleness as commit distance: useful revision context without claiming that a commit count alone proves semantic obsolescence.
<!-- evidence: ev-4f8eca4156d50ba0 -->

Its first useful result was unfavorable. All 24 governed artifacts predate the current browser sources: the 13 mock artifacts by one commit and the 11 live artifacts by three. That is evidence infrastructure doing its job. It did not decorate the corpus with a reassuring freshness label; it made the corpus able to disclose its own limits.
<!-- evidence: ev-4f8eca4156d50ba0 -->

The gap matters because student-facing assignment summaries now show current, latest, and best scores, completed runs, total attempts, and last activity, while catalog browse, search, and detail routes are restricted server-side to Instructor and Sysadmin roles. The project also names 1280×800 as the canonical laptop viewport and 800×1280 portrait tablet as a high-priority student target. Yet none of the six student surfaces has governed portrait-tablet evidence, and one committed screenshot has neither a producing pipeline nor a citing document.
<!-- evidence: ev-4f8eca4156d50ba0 -->

The next task is reconciliation rather than indiscriminate capture: decide which committed images belong under governance, then refresh the changed student routes where the declared device contract says evidence matters most.
<!-- evidence: ev-4f8eca4156d50ba0 -->

## Facts should not become convenient conclusions

The inventory-system roadmap in [brick-collection](https://github.com/vosslab/brick-collection) applies the same boundary to physical stock. Existing scripts can price parts, generate labels, perform catalog lookups, and prepare Sheets-ready data, but those utilities cannot establish which physical copy is being discussed, where it sits, what receipt supports its cost, or whether its observed condition supports a marketplace listing.
<!-- evidence: ev-0b2162a70df48d35 -->

The proposal gives specialized tools bounded roles beneath one authoritative ledger. `ledger.sqlite` would hold durable operational and accounting facts such as acquisition cost, evidence, quantities, locations, and transformations. `analysis.sqlite` would hold rebuildable market snapshots, assumptions, forecasts, and recommendations. Sheets would become a generated dashboard and evidence source; BrickStore would remain controlled operational staging; BrickLink would remain the sales and market-data channel.
<!-- evidence: ev-0b2162a70df48d35 -->

The important restraint is that unknown cost, uncertain completeness, unmapped lots, and quantity mismatches remain visible review work rather than becoming invented values or convenient zeroes. This is still a roadmap, not an implemented operational system. Its credible first proof is narrow: evidence-backed intake, distinct stock lots, locations and movements, structured condition observations, and an exception queue.
<!-- evidence: ev-0b2162a70df48d35 -->

[battery-control](https://github.com/vosslab/battery-control) supplied a smaller operational version of the same idea. It gained 135 hourly records through August 18 at 13:00, preserving price, moving median, cutoff, state-of-charge transition, recorded flows, price classification, strategy label, and reserve values together. The result is an inspectable trace of operation rather than an anecdote about what the controller probably did.
<!-- evidence: ev-23a83ecd456dbdbf -->

The trace retains the inconvenient hours. On August 14 at 06:00, the price was 13.7 against a 9.2 cutoff and classified `above_cutoff`, while state of charge began and ended the hour at 20%. That observation does not establish success, failure, causation, grid-import savings, or economic benefit. It preserves the context needed to investigate those questions without claiming their answer in advance.
<!-- evidence: ev-23a83ecd456dbdbf -->

The day’s movement was not automation for its own sake. It was making artifacts answerable: a converted book can disclose its stages, a screenshot can disclose its route and revision context, an inventory record can keep facts separate from estimates, and an operational trace can preserve evidence without claiming victory. The unfinished work is where that discipline becomes most valuable: prove the book-conversion handoff end to end, add spread-scan fixtures, reconcile the student evidence gap, and evaluate controller outcomes against a baseline instead of confidence by implication.
<!-- evidence: ev-c64f2ec7dbe5afad, ev-9dc90ec3afaf41cf, ev-4f8eca4156d50ba0, ev-0b2162a70df48d35, ev-23a83ecd456dbdbf -->

## Project coverage

- vosslab/battery-control
- vosslab/book-to-markdown
- vosslab/brick-collection
- vosslab/peptidyle-learning-engine
- vosslab/vosslab-skills
