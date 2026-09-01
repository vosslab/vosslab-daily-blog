---
date: 2026-08-26
slug: making-the-interface-tell-the-truth
generator_run: 20260828T003950Z-bdee87fdc1
evidence_manifest: evidence.json
editorial_projection: editorial_projection.json
---

# Making the Interface Tell the Truth

Today’s strongest thread was making complex systems honest at their boundaries: an instructor can enter a real assignment workspace without becoming a fabricated student, a chemistry tool can preserve native input intent through its controller, and course materials can share one source of truth across web and export formats. <!-- evidence: ev-2bd59f1e08feeea0, ev-a4532745471577cf, ev-abf41f8ac83dbb37 -->

<!-- more -->

## An instructor workspace that keeps its authority

I advanced Peptidyle Learning Engine’s instructor experience from a collection of assignment links toward a coherent workspace. The new Overview, Questions, Policies, and Student-view routes load through the same course-authorized assignment path; assignment titles now open the Instructor Overview; and the Student view reuses an answer-free learner landing without changing the instructor’s identity or mutating learner data. That is a deliberately narrow design: it gives instructors a familiar way to inspect what students see while preserving the system’s ordinary enrollment and grading authority. <!-- evidence: ev-2bd59f1e08feeea0, ev-2bd59f1e08feeea0 -->

![Instructor assignment access preview](../../assets/publications/2026-08-26/4e631a9ea189-01_access_preview_allowed.png)

The surrounding live-demo work made that boundary operational rather than merely architectural. I made shared instructor–student course relationships explicit, verified a learner’s persisted scores and completed runs in the instructor gradebook projection, moved long-lived demo control records out of Cargo’s disposable build tree, and made rerunning the root demo command replace its active owner cleanly. The production-shaped stack then passed its connected browser journeys, migration and persistence checks, and clean-up receipts; the next named handoff is WP-PROF-G1 after acceptance of the curriculum-adoption slice. <!-- evidence: ev-2bd59f1e08feeea0, ev-2bd59f1e08feeea0 -->

## One source of truth, from syllabus to chemical canvas

In the syllabus repository, I treated maintainability as a student-facing feature. A single repository-owned include engine now supplies the same authorized Markdown expansion to the MkDocs site and complete DOCX/PDF builder, while a canonical term-course fragment feeds both the main page and term overview. The validation front door now runs fast tests, complete-export checks, a strict site build, the Pages builder, and Playwright; that makes shared source material less likely to drift between the page students read and the documents they download. <!-- evidence: ev-abf41f8ac83dbb37 -->

Ferrum Chemical Forge applied the same principle to an interactive desktop surface. I finished the ninth attached compact-group recipe—phenyl—completing the nine-recipe catalog, with a generic Rust materialization contract that preserves exterior-bond identity and supports both directed attachment orientations. I also consolidated menu and ribbon behavior around registry-owned Qt actions: declarative YAML controls placement, while each feature keeps its own activation, normalized input dispatch, cancellation, checked state, shortcuts, and accessibility. The public installed attachment workflow reported success and a usable scene, while full M4 and Rust/OASA/BKChem parity remain explicitly unfinished. <!-- evidence: ev-a4532745471577cf, ev-a4532745471577cf -->

## Reliability includes the assets and the rules around them

The virtual lab work closed a different but related gap: when visual assets are part of the experiment, the review route must exercise what actually ships. I replaced a rejected cubist equipment-art direction with physically credible laboratory forms, removed duplicate or misleading state models for vessels, electrophoresis leads, and gel combs, and added both file-based and production-host review galleries. The recovered tree’s build, Python, Node, and Playwright gates passed, and the production host reviewed all 130 current cards without load or render-mode failures. <!-- evidence: ev-477e8c08187b1b82 -->

I also strengthened the repository template that carries these practices outward. License propagation now migrates recognized legacy forms safely while preserving ambiguous or customized legal files; reset installs use recognizable plain-text `LICENSE.<SPDX>` names; and the documented policy distinguishes universal managed ignore rules from repository-owned local rules. The day’s remaining question is how far this shared discipline can travel without turning a template into an overgrown central authority: the new Graphify documentation option deliberately keeps repository-specific exclusions authoritative. <!-- evidence: ev-2b6320456ce7b017, ev-2b6320456ce7b017 -->

## Project coverage

**vosslab/ferrum-chemical-forge** completed its nine-recipe attached compact-group catalog with phenyl and strengthened the Qt ownership model for native input, close lifecycle decisions, action dispatch, and declarative menu/ribbon clients; the installed workflow and full test suite passed, while parity work and manual accessibility evidence remain open. <!-- evidence: ev-a4532745471577cf -->

**vosslab/peptidyle-learning-engine** added the instructor assignment workspace and student-view landing, completed curriculum-adoption and live-demo reliability work, refreshed documentation and 75 published screenshots, and passed the connected production-stack, PostgreSQL/RLS, browser, Rust, Node, and pytest gates. <!-- evidence: ev-2bd59f1e08feeea0 -->

**vosslab/starter-repo-template** introduced safe legacy-license migration, plain-text SPDX license conventions, a canonical ignore-policy system, and optional documentation-inclusive Graphify extraction, with focused and complete test suites recorded as passing. <!-- evidence: ev-2b6320456ce7b017 -->

**vosslab/syllabus** added shared Markdown inclusion for site and document production, canonical course and extra-credit sources, automated link and production checks, accessible site refinements, and a single executable validation front door. <!-- evidence: ev-abf41f8ac83dbb37 -->

**vosslab/virtual-lab-protocol-simulation** rebuilt reviewed laboratory equipment assets, clarified state ownership for several apparatuses, and added current-library review pages that use the production SVG host; the reported build and browser validation gates passed. <!-- evidence: ev-477e8c08187b1b82 -->

**vosslab/vosslab-skills** reframed related-project documentation as visitor discovery rather than dependency cataloging, updated the writing template and guidance accordingly, normalized skill metadata, and passed 1,077 collected validation tests. <!-- evidence: ev-5e482d9bfbaeb94c -->
