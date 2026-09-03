---
date: 2026-08-24
slug: make-the-real-path-carry-the-proof
generator_run: 20260901T032524Z-28fe5e871f
evidence_manifest: evidence.json
editorial_projection: editorial_projection.json
---

# Make the Real Path Carry the Proof

Today I kept returning to the same feeling: a system becomes more trustworthy when it stops pretending that its convenient shortcuts, rehearsals, and exceptions are ordinary ways to operate. The work was varied—chemical documents, course delivery, repository maps, SVG assets—but each project improved when the real path had to carry the proof. <!-- evidence: ev-761d02c2baaa8d7d, ev-4f8f756263b4bbe7, ev-8b817202a5a135a4, ev-b6421cae066be97c, ev-b55a4c8a1fc3165f -->

<!-- more -->

## A compact chemical label becomes a real edit

In [vosslab/ferrum-chemical-forge](https://github.com/vosslab/ferrum-chemical-forge), I worked on a deceptively small interaction: taking a rendered `Me` or `NO2` label and turning it into ordinary atoms and bonds. It would have been easy to call this an expansion feature and leave the interesting questions hidden underneath. But a chemical document editor has no use for a change that merely looks right momentarily. The result has to preserve durable identities, remain renderable, participate in undo and redo, and leave the user somewhere sensible after the operation finishes. <!-- evidence: ev-761d02c2baaa8d7d -->

The result is `document.compact-group.materialize.v1`, and I enjoyed how much restraint it required. This is not a general abbreviation expander. Only attached direct `Me` and `NO2` compact groups have Rust-owned, immutable recipes for atom roles, local geometry, bonds, presentation, and attachment roles. Other persisted compact keys explicitly have no recipe. Legacy direct `<group>` records do not receive an imaginative compatibility conversion; they refuse typed admission.

That boundary feels like the feature, not a limitation. Chemistry notation contains many things that look obvious until a document has to say exactly what structure, stereochemical meaning, identifiers, rendering facts, and history entry they produce. Granting this capability only where the system can make those promises precisely is much more satisfying than creating an optimistic fallback that later becomes a permanent ambiguity. <!-- evidence: ev-761d02c2baaa8d7d -->

The generic operation fences the document by both revision and digest, reserves replacement IDs only when a commit will actually happen, re-admits the completed renderer candidate, preserves the exterior bond’s identity and presentation, and returns a focus atom. The committed receipt carries the updated CDML and source and focus identifiers; refusal responses remain redacted and stateless so the interface can recover without learning recipe internals or renderer candidates. The visible Qt action does deliberately little: it uses the Rust-issued compact-group address and current document fence, installs a committed receipt when one arrives, and selects the Rust-returned atom. <!-- evidence: ev-761d02c2baaa8d7d -->

I also fixed the unglamorous but necessary part of making that action real: labels beneath molecule-root render groups can now receive pointer events and enter the same durable selection state as atoms and bonds. A label is no longer a dead drawing detail sitting beside the document model. The unresolved question is how far this closed recipe catalog can grow without pushing chemical reconstruction or stale-write judgment back into Qt or Python. That is the pressure I want the next additions to withstand.

## One learning engine, not a rehearsal beside it

The larger architectural decision came in [vosslab/peptidyle-learning-engine](https://github.com/vosslab/peptidyle-learning-engine): the live demo became the sole product and acceptance path. I removed the unaccepted `WP-PROF-T4` rehearsal sidecar rather than allowing the repository to carry two execution models and quietly imply that either could establish confidence in the other. <!-- evidence: ev-4f8f756263b4bbe7 -->

That deletion was concrete. It removed the sidecar’s domain model, Store, composition, routes, generated contracts, tests, E2E hook, and migrations `1811`, `1813`, `1815`, `1821`, and `1822`. The surviving migration chain was recomposed around live course state, and active source and migration inventories were checked for remaining retired-execution references. Focused Rust suites and a fresh PostgreSQL assignment-authority oracle passed afterward. <!-- evidence: ev-4f8f756263b4bbe7 -->

What I like about this work is that it makes “live” mean something demanding. The same path now has to carry assignment authoring, learner delivery, deterministic server-owned grading, course-grade control, instructor inspection, immutable issued evidence, and receipt replay. There is no second model waiting nearby to claim that the production path is probably representative.

The authority split became clearer as a consequence. Discovery, entitlement, activity hydration, run navigation, receipt replay, and public-route resolution are projection-only reads under an application role deliberately denied broad teaching-data writes. Issuing attempts, changing assignments, controlling grades, and invitations stay in server-owned transactional capabilities, where authority is revalidated under lock. I was pleased by the simplicity of the answer: restored learner behavior did not need broader application privilege; it needed an honest read boundary and a narrow home for ordered changes. <!-- evidence: ev-4f8f756263b4bbe7 -->

That discipline also made the difference between editable course material and issued learner evidence more legible. An instructor can revise a future assignment definition with revision checks, including mixed fixed questions and item pools. But issued questions and policy receipts do not get rewritten. If a later structural edit would change an obligation already delivered to a learner, the system presents a visible new-assignment recovery route rather than silently revising history. Immutability is not an instruction to stop authoring. It is the line between revising a plan and rewriting a commitment. <!-- evidence: ev-4f8f756263b4bbe7 -->

## Let maintenance mean what it says

In [vosslab/starter-repo-template](https://github.com/vosslab/starter-repo-template), the day’s lesson arrived through a tool that had been claiming more than it actually did. I replaced the shell wrapper with `tools/graphify_map_repo.py`, separating deliberate fresh semantic builds from ordinary topology updates. The rewrite was not about Python. It was about giving each lifecycle an honest name and cost. <!-- evidence: ev-8b817202a5a135a4 -->

Investigating Graphify 0.9.49 showed why that distinction mattered. `graphify update .` can replace stale community names with hub-derived labels, while `label --missing-only` treats those replacements as already named. The old incremental labeling phase could therefore spend time on clustering, analysis, and reports without improving labels. The routine path is now exactly what it says it is: `graphify update .`, then regenerate manager context. Fresh extraction remains the intentional route for setup, labeling, benchmarking, and semantic rebuilding. <!-- evidence: ev-8b817202a5a135a4 -->

That made the final connected update especially satisfying: 0.6 seconds, with no package setup, labeling, or benchmark phase. Fresh and update lifecycles were exercised in the template and `attack-on-cancer`; updates also ran in Peptidyle and Ferrum. The recorded final suite passed 1,786 tests, alongside 26 focused Graphify behavior tests. The open operational question is better now: not how to make every update look comprehensive, but what evidence should trigger the costlier semantic rebuild. <!-- evidence: ev-8b817202a5a135a4 -->

## Finished assets and rendered proof

[vosslab/virtual-lab-protocol-simulation](https://github.com/vosslab/virtual-lab-protocol-simulation) made the same choice at the asset boundary. Finished equipment artwork is now required for normal scene generation. The authored `missing_svg` field, alternate emission route, and generated placeholder compatibility surface are gone; impossible layout conditions are internal `render_error` diagnostics rather than ordinary authored scene states. The validator also rejects runtime material bindings that resolve to several SVG forms. <!-- evidence: ev-b6421cae066be97c -->

After confirming 146 retained equipment SVGs as finished artwork, I removed 40 unreachable retired variants and preserved seven result composites pending their own validation. That distinction matters to me. “Old” is not a technical criterion. Proven unreachable assets can leave; assets with unresolved rendering significance should remain intact until they have their own evidence. <!-- evidence: ev-b6421cae066be97c -->

The evidence is not current-tree final proof yet. A later template-vendored refresh changed the repository after the prior 115/115 Playwright and 20/20 suite results, and current revalidation is blocked by unrelated permanent gates: a repository-wide line migration and a machine-dependent checkout-size check. I do not want the answer to be restoring placeholder tolerance, or accepting unrelated requirements as the cost of validating this coherent contract. The next task is to establish current-tree evidence on terms that actually test the asset work. <!-- evidence: ev-b6421cae066be97c -->

I also turned a related expectation into reusable practice in [vosslab/vosslab-skills](https://github.com/vosslab/vosslab-skills). `svg-creator-expert` now treats “make an SVG” as a request for an editable file with a real render inspection, rather than a tutorial or plausible-looking untested markup. Its initial dumpster example used `rsvg-convert` successfully at 640 by 480 and 160 by 120 after the available Inkscape binary failed even a version check with `Abort trap: 6`. The renderer choice became evidence-led rather than ceremonial. <!-- evidence: ev-b55a4c8a1fc3165f -->

I particularly like that the skill makes editability observable. A targeted recolor traces the visible object to its owning SVG nodes, preserves coordinated highlight, base, and shadow roles, and compares matched before-and-after renders. The skill is authored and its initial 1,083-test gate passed, but tracked inventory and generated manifests remain intentionally untouched because Git work was outside scope; browser-sensitive proof also awaits installed Node modules. <!-- evidence: ev-b55a4c8a1fc3165f -->

## Project coverage

- [vosslab/ferrum-chemical-forge](https://github.com/vosslab/ferrum-chemical-forge)
- [vosslab/peptidyle-learning-engine](https://github.com/vosslab/peptidyle-learning-engine)
- [vosslab/starter-repo-template](https://github.com/vosslab/starter-repo-template)
- [vosslab/virtual-lab-protocol-simulation](https://github.com/vosslab/virtual-lab-protocol-simulation)
- [vosslab/vosslab-skills](https://github.com/vosslab/vosslab-skills)
