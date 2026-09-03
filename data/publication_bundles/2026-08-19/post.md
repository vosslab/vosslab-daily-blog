---
date: 2026-08-19
slug: authority-before-interface
generator_run: 20260901T153400Z-57b63919c8
evidence_manifest: evidence.json
editorial_projection: editorial_projection.json
---

# Authority Before Interface

Today I kept returning to a question that sounds smaller than it is: when a learner opens an assignment, what exactly is the system entitled to tell them? In [vosslab/peptidyle-learning-engine](https://github.com/vosslab/peptidyle-learning-engine), I worked on making the answer a sequence of accountable decisions rather than an accident of roster state, browser routing, and whatever data happened to be available. <!-- evidence: ev-ad203f105bd016be, ev-9be630593bac18cf -->

<!-- more -->

## The decision has to come before the screen

The work settled into three distinct questions. First: is this learner currently entitled to use this assignment? Second: which policy governs this particular attempt? Third: given that policy and the current time, what may the learner see? Those became WP-PROF-S5, WP-PROF-S3, and WP-PROF-S4. Separating them was satisfying because it removed a temptation that shows up in learning software everywhere: let the interface or a convenient stored field quietly answer an authority question it was never designed to own. <!-- evidence: ev-ad203f105bd016be -->

The most important correction was ending the automatic cross-product between active roster membership and assignment enrollment. Being on a roster no longer eagerly produces an enrollment record for every assignment. Instead, a learner or instructor action that actually needs entitlement evaluates current membership and assignment audience inside its transaction. If access is warranted, the system materializes exactly one receipt and preserves whether it came from an actor or a rule. Revoking access or narrowing an audience can change what is allowed now without rewriting the historical evidence of what had previously been true. <!-- evidence: ev-ad203f105bd016be -->

That is a more honest model of time. Reinviting someone creates a new membership episode while retaining their course-local identity and prior records. The system does not pretend that yesterday's authorization is a timeless fact, but it also does not erase the trail behind a later decision.

## Keeping the authority trail

S5 establishes the source material for entitlement: closed assignment audiences, canonical course-membership episodes, purpose-capable groups, evaluator-issued applicable-policy scopes, and immutable provenance for materialized receipts. I put those under one typed Rust domain and Store contract, with PostgreSQL representing the relationships directly instead of keeping a JSON shadow model that downstream code would have to reinterpret. Memory and PostgreSQL now compose the same evaluator-approved scopes across resolve, start, issue, and list paths. <!-- evidence: ev-ad203f105bd016be -->

Then S3 consumes that authority rather than trying to reconstruct it. The effective-assignment-policy resolver is deliberately pure: lifecycle, entitlement, and authorization gates deny before group modifiers or individual exceptions can resolve per-field policy. That ordering closes a subtle but consequential gap. An unrelated group modifier cannot suppress someone who is otherwise currently entitled to the assignment. <!-- evidence: ev-ad203f105bd016be -->

I enjoyed the insistence that policy outcomes are themselves evidence. Resolved attempt policy is stored in append-only sealed receipts with per-field source rows; the current pointer may point only to a sealed generation. PostgreSQL does not seal a set until it has one grant basis and a complete applicable-scope set, and the database boundary rejects late-scope insertion, direct application writes, cross-tenant reads, reversible membership episodes, and unauthorized instructor provenance. A value alone can look decisive while concealing the conditions that produced it. I wanted the system to retain those conditions. <!-- evidence: ev-ad203f105bd016be -->

## Withholding is not a zero

S4 was where that chain became visible to learners. Score, correctness, feedback text, solution, and class statistics now each have an assignment-owned closed timing. Learner-facing projections take only current entitlement, the current S3-resolved verdict, authoritative server time, and submission fact. They omit the instructor policy, tenant, clock, and raw-storage authority inputs that do not belong in a learner response. <!-- evidence: ev-ad203f105bd016be -->

The part I care about most is negative space. A withheld score must not become a misleading zero. A neutral state must not promise a future release the assignment has not authorized. The surviving `feedback_release` field remains audit evidence only; it cannot change disclosure. Data existing in storage and data being permitted to enter a learner's view are different facts, and the API now treats them that way. <!-- evidence: ev-ad203f105bd016be -->

The class-statistics rule makes that concrete. The learner-safe projection is identity-free, omits withheld information, and reports insufficient evidence without inventing a metric. Only at the fixed five-learner floor can it disclose a cohort size and normalized average. It is a small rule with a useful discipline behind it: incomplete evidence should look incomplete. <!-- evidence: ev-ad203f105bd016be -->

## The browser should reflect the boundary, not create it

The browser work followed the same direction. A central route-role contract runs before instructor components, course-theme reads, or transport mounting. Learners can reach learner assignment, run, and account pages, while instructor-only deep links such as roster and gradebook receive accessible denials. Direct navigation, reload, and no-transport tests carry the authorization proof; screenshots help make the intended experience inspectable, but they are not the proof by themselves. <!-- evidence: ev-ad203f105bd016be, ev-9be630593bac18cf -->

![Instructor assignment overview](../../assets/publications/2026-08-19/d5272618ef57-instructor_page_assignment_overview.png)

I like that the visible result is quieter than the underlying work. The instructor page can remain an ordinary assignment overview while the system behind it has become much clearer about who can see which route, which result, and why.

The unresolved question is how this model feels when it meets the less orderly realities of a course: changing audiences, late accommodations, unusual group rules, and instructor expectations formed by older tools. The contracts are deliberately strict now. The next useful work is not to blur them for convenience, but to learn where the interfaces need better explanations without turning explanation into a second source of authority.

## Project coverage

- vosslab/biology-problems
- vosslab/biology-problems-website
- vosslab/ferrum-chemical-forge
- vosslab/peptidyle-learning-engine
- vosslab/starter-repo-template
- vosslab/track-runner-virtual-dolly-cam
