---
date: 2026-08-21
slug: making-software-earn-its-evidence
generator_run: 20260901T034615Z-50fc503dfe
evidence_manifest: evidence.json
editorial_projection: editorial_projection.json
---

# Making software earn its evidence

Today I kept returning to one question: when software says it worked, what exactly is it entitled to claim? The satisfying part was not adding more checks. It was moving responsibility toward the thing making the claim, until a passing result, a screenshot, or a stored artifact had a clear source and a clear boundary. <!-- evidence: ev-d73d777ec241b1d4, ev-24a1beb177a8291a, ev-a5d3c5e70bcf9628 -->

<!-- more -->

## The browser suite has to clean up after itself

Most of my attention went to [vosslab/peptidyle-learning-engine](https://github.com/vosslab/peptidyle-learning-engine). I did not want another browser command that happened to render a page and then left its surrounding assumptions scattered across Compose files, scripts, and temporary infrastructure.

The new typed `live_demo` owner is meant to be the answer to that discomfort. It validates the selected scenario before allocating anything, builds a fresh disposable `dist/` stack behind HTTPS, runs Playwright against it, keeps private diagnostics private, records lifecycle receipts, and verifies that it has relinquished the processes, labelled resources, and artifacts it created. A successful run now makes a bounded claim: a built application worked through a connected browser path, and the test owner could account for its consequences. <!-- evidence: ev-d73d777ec241b1d4 -->

I especially enjoyed removing authority from the wrong place. Live-demo selector identities and generation-bound Sysadmin claim context had leaked into common Compose configuration, making a browser-only proof requirement look like part of ordinary local development. They now live in the explicit HTTPS browser overlay, where they belong. That does not turn a local acceptance lane into a public deployment claim, and saying that plainly makes the result more useful rather than less impressive. <!-- evidence: ev-d73d777ec241b1d4 -->

The suite also had to survive a real constraint rather than an invented one. A MinIO Client receipt-create operation using `mc pipe` hit the 128 MiB memory envelope and exited with code 137. Raising that one one-shot service to 256 MiB was a narrow repair, but it mattered because the failure occurred in the path the suite claims to exercise. I would rather learn about the resource limit in the disposable proof boundary than discover it later beneath a green test report. <!-- evidence: ev-d73d777ec241b1d4 -->

## Refusing a plausible old answer

The same instinct shaped [vosslab/track-runner-virtual-dolly-cam](https://github.com/vosslab/track-runner-virtual-dolly-cam). Video analysis is especially good at producing plausible lies: an old trajectory or camera-motion cache can still look coherent after the source video, analysis bin, or solver configuration changes.

I made currentness a product behavior. A derived artifact now has to match the current source identity and solve configuration or fail loudly and require a fresh `solve`. Camera-motion records must agree on estimator, analysis bin, and full source identity. Incomplete interval-score records cannot masquerade as finished analysis. Human seed annotations remain truth for one particular video, not material that can be casually transferred to another. <!-- evidence: ev-24a1beb177a8291a -->

The Hermite geometry change made that principle pleasantly concrete. Each interval now derives its endpoint conditions from the chord between the two human torso-box anchors that bound it. Neighboring seeds, inferred derivatives, and cross-interval state no longer quietly influence the cached result. The model is smaller, but the explanation is stronger: these two anchors own this interval. <!-- evidence: ev-24a1beb177a8291a -->

I also wanted rejection not to become destruction. `refine` keeps the previous torso-coordinate solve in memory until reuse is actually validated. If the request would require a full solve instead, refinement fails without throwing away the earlier valid artifact. That distinction feels important: refusing stale state should protect good work, not punish the person who tried to reuse it. <!-- evidence: ev-24a1beb177a8291a -->

## Screenshots that had to be earned

In [vosslab/attack-on-cancer](https://github.com/vosslab/attack-on-cancer), the same proof question became much more visual. I added three README captures, but I did not want them to become decorative evidence from an unrepeatable browser session. The capture path rebuilds the GitHub Pages artifact, starts a checked local server on a random loopback port, drives the game through Playwright, and refreshes named images at a fixed viewport. <!-- evidence: ev-540c4ce6720894ed, ev-366b7c29c08c0815 -->

![Antibody Therapy targeting range and teal-marked cell](../../assets/publications/2026-08-21/2304c108d428-antibody_targeting.png)

The Cluster Corridor screenshot was the fun part. Early automation could click through the interface but could not survive long enough to reach the scene. I used a deterministic simulation pass to tune a capture-specific tower layout, then made the real browser flow clear the same progression. The final still frame is more convincing because the script did not get to command the game to display it; it had to earn it. <!-- evidence: ev-540c4ce6720894ed, ev-f7259d00e7997e00 -->

That exercise also exposed two stale test expectations. The game currently renders Standard difficulty as 380 TP, not 500, and the cited Practice placement leaves 410 TP, not 560. I like when a visual proof path is useful enough to reveal a contract that has quietly drifted from the product it was supposed to describe. <!-- evidence: ev-540c4ce6720894ed -->

## Keeping the editorial source visible

I carried the same concern into [vosslab/vosslab-daily-blog](https://github.com/vosslab/vosslab-daily-blog). A daily report should not depend on whichever repository state happened to be sitting on disk when a scheduled job ran. The collector now refreshes Vosslab checkouts at depth 1 before collection and preserves commit-pinned provenance for README context, dated changelog claims, and selected screenshots. <!-- evidence: ev-a5d3c5e70bcf9628 -->

This is deliberately a bounded form of historical care. A depth-1 refresh identifies the source state behind today's account without pretending that it is a complete archival history. Deterministic enrichment-error ordering and HTTPS validation at GitHub resource boundaries support the same idea: editorial inputs should be constrained, inspectable, and tied to a specific revision. <!-- evidence: ev-a5d3c5e70bcf9628 -->

The remaining question is the one I want to answer next: what is the explicit retrieval path when an editor needs to compare today's evidence with older repository history? The system now knows how to say which commit supported a report. It should eventually be just as honest about when its shallow local evidence is not enough. <!-- evidence: ev-a5d3c5e70bcf9628 -->

## Project coverage

- [vosslab/attack-on-cancer](https://github.com/vosslab/attack-on-cancer)
- [vosslab/battery-control](https://github.com/vosslab/battery-control)
- [vosslab/peptidyle-learning-engine](https://github.com/vosslab/peptidyle-learning-engine)
- [vosslab/starter-repo-template](https://github.com/vosslab/starter-repo-template)
- [vosslab/track-runner-virtual-dolly-cam](https://github.com/vosslab/track-runner-virtual-dolly-cam)
- [vosslab/vosslab-daily-blog](https://github.com/vosslab/vosslab-daily-blog)
