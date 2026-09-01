---
date: 2026-08-29
slug: making-the-next-decision-legible
generator_run: 20260831T160403Z-7dcd9282b4
evidence_manifest: evidence.json
editorial_projection: editorial_projection.json
---

# Making the Next Decision Legible

The day began with a practical question: when someone reaches a decision point in software, can they see what matters next, understand what it will change, and trust that the system will actually let them do it? That question connected two games with very different tempos and the publishing workflow that documents their work.  
<!-- evidence: ev-29dd707a60332a35, ev-a481260b3fe33d91, ev-d75edf78d643ef87, ev-0501f010e82d7544 -->

<!-- more -->

## The first cell has to feel like an invitation

In [Cancer Clicker NG](https://github.com/vosslab/cancer-clicker-ng), the opening board had accumulated ambiguity that was easy to miss once I already knew the game: unclear price semantics, clipped tooltips, fractional-cell wording, future systems shown before they mattered, and a central visual that did not clearly explain the first action.  
<!-- evidence: ev-29dd707a60332a35 -->

The corrective work was satisfying because it did not require adding more explanation. It made the living tumor the direct target for manual growth: divide a rendered cell, receive local `+1 cell` feedback, and see the total update in the same arena. Forgiving nearby-pointer envelopes let individual cells remain approachable targets without turning the tissue into a generic button.  
<!-- evidence: ev-29dd707a60332a35, ev-a481260b3fe33d91 -->

![A newly available hallmark decision in Cancer Clicker NG](../../assets/publications/2026-08-29/bf6b959a691b-hallmark_acquisition.png)

The surrounding interface now earns its space by answering the next questions where they arise. Growth states the objective, whole-number requirement, instruction, and destination action. Each discovered Upgrade Rack row exposes Owned, Output, Buy, Cost, and Adds. Later systems stay absent until durable progress makes them actionable, so the player can recognize the current decision instead of memorizing notation or hunting through help text.  
<!-- evidence: ev-29dd707a60332a35, ev-a481260b3fe33d91 -->

## A visible option must lead somewhere real

The more consequential repair was underneath the screen. A canonical first hallmark purchase can be visibly available and still fail if sparse ownership state treats a missing record as an error. The state model now interprets absent hallmark ownership as implicit level zero, allowing that first visible purchase to create its initial durable record.  
<!-- evidence: ev-a481260b3fe33d91, ev-29dd707a60332a35 -->

That small transition clarified the day’s larger lesson: progressive disclosure is not decoration placed over a finished model. Rendering, progress prerequisites, and durable state transitions have to agree about what is possible. If the screen teaches “you can do this now” while the model refuses the action, the interface has made a broken promise.  
<!-- evidence: ev-a481260b3fe33d91, ev-29dd707a60332a35 -->

The visual review is useful partly because it does not pretend to prove more than it can. It covers production-built opening, recovery, offline-return, responsive, tooltip, accessibility, and interaction states, including 29 responsive and interaction frames. It establishes that intended routes can be rendered and exercised; it does not establish that first-time biology students understand every term, icon, or longer-run progression choice.  
<!-- evidence: ev-29dd707a60332a35 -->

## Tier information belongs in the battle

[Attack on Cancer](https://github.com/vosslab/attack-on-cancer) faced the same problem at a faster pace. A player must read routes, moving cells, range indicators, placement constraints, effects, and wave controls. Its four treatment tiers already existed, but subtle pips were too easy to lose in the field.  
<!-- evidence: ev-d75edf78d643ef87, ev-1f2a67ac31c507de -->

The replacement is a high-contrast lower-right Tier 1–4 crest with a distinct geometric glyph, backed by a four-step selected-treatment ladder that distinguishes completed, current, and next available upgrades. The point is not louder decoration; it is making consequential treatment state available where a player decides whether to place, upgrade, rebuild, or sell.  
<!-- evidence: ev-d75edf78d643ef87, ev-3d1c098a11379c7d, ev-1f2a67ac31c507de -->

The visual claim also travels through the implementation. Tier state reaches typed configuration, tower state, inspector UI, combat rendering, and attack effects; effects receive a visual-tier attribute, derive timing from per-treatment tier configuration, and expose stable SVG styling hooks. Chemotherapy supplies one bounded mechanical consequence: its splash radius progresses from 48 to 58, 72, and 90 across the four tiers, while the other combat rules remain unchanged.  
<!-- evidence: ev-d75edf78d643ef87, ev-3d1c098a11379c7d, ev-1f2a67ac31c507de -->

That constraint makes the progression more believable. A player can see a treatment’s state and connect it to a specific consequence instead of being asked to accept that a higher tier is simply “stronger.” The project’s fast checks passed build, typecheck, lint, formatting, Node tests, and 958 pytest cases.  
<!-- evidence: ev-d75edf78d643ef87 -->

## Evidence needs a clear completion rule too

The same concern appeared in [vosslab-podcast](https://github.com/vosslab/vosslab-podcast), where the maker-voice fixup preserved the descriptor snapshot that the acceptance path evaluates. That closes a time-of-check/time-of-use boundary: the thing being accepted cannot silently become a different thing before completion is determined.  
<!-- evidence: ev-0501f010e82d7544 -->

Final acceptance remains fixture-backed. Live-model behavior is useful corroboration, but neither nondeterministic model output nor human approval decides whether the workflow is complete. That separation matters because screenshots, deterministic tests, browser exercises, live-model runs, and human review answer different questions; they should not be casually substituted for one another.  
<!-- evidence: ev-0501f010e82d7544, ev-29dd707a60332a35 -->

The accepted workflow record includes 2,450 producer tests on Python 3.12.13, 1,362 publisher tests on Python 3.13.5, 310 publisher-hygiene tests, a strict disposable MkDocs build, publication, scheduling, and 12-case crash exercises, independent audits, and matching approved prompt hashes. The value is not the totals alone, but being able to identify what each form of evidence actually supports.  
<!-- evidence: ev-0501f010e82d7544 -->

The unresolved edge is empirical. Cancer Clicker NG now has evidence that its opening action, help, recovery routes, and progression are visible and state-consistent, but not evidence that new biology students can explain manual versus automatic growth, a molecular-machine purchase, or a newly enabled hallmark decision after play. That needs participant sessions rather than another layer of interface gates.  
<!-- evidence: ev-29dd707a60332a35 -->

Attack on Cancer has a related future probe: a proposed anti-angiogenesis treatment could slow cell progress through blood-vessel constriction. If it becomes part of the game, its map-wide effect will need to remain as legible in the field as tower tier is now. The publishing workflow likewise still needs a way to retain longitudinal optional live-model observations without letting nondeterminism return as a release gate.  
<!-- evidence: ev-4ed061aa94fd8d85, ev-0501f010e82d7544 -->

The standard that emerged is simple: a system earns trust when its next available action, its material consequence, and the evidence that it worked can stay close enough to be understood together.  
<!-- evidence: ev-29dd707a60332a35, ev-a481260b3fe33d91, ev-d75edf78d643ef87, ev-0501f010e82d7544 -->

## Project coverage

- [vosslab/attack-on-cancer](https://github.com/vosslab/attack-on-cancer)
- [vosslab/cancer-clicker-ng](https://github.com/vosslab/cancer-clicker-ng)
- [vosslab/vosslab-podcast](https://github.com/vosslab/vosslab-podcast)
