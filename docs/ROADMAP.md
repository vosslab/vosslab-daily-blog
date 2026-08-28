# Roadmap

This roadmap records planned publisher work that has concrete repository evidence but remains
unstarted or unsettled. It does not alter the producer-owned bundle contract.

## Priority 1: Consolidate strict-build execution

Presentation publication now has one Python 3.13 contract with an optional virtual environment, but
the importer and presentation publisher still launch strict MkDocs builds through separate helpers.

- Extract one typed strict-build runner shared by
  [scripts/site_deployment.py](../scripts/site_deployment.py) and
  [scripts/import_publication_bundle.py](../scripts/import_publication_bundle.py).
- Make bundle import and presentation publication use the same interpreter and dependency checks.
- Replace the untyped build callback contracts with one explicit callable protocol or alias.
- Verify both publication routes preserve the same build failure and last-good-release semantics.

**Owner.** Publisher runtime and documentation maintainers.

## Priority 2: Separate publication-admission policy from presentation work

The current working tree changes [scripts/validate_daily_post.py](../scripts/validate_daily_post.py)
to allow up to three uncited narrative blocks. That admission-policy change is independent of the
presentation deployment and must receive its own contract decision.

- Decide whether the allowance belongs in the producer-to-publisher publication contract.
- If adopted, coordinate an explicit contract version and producer implementation with
  `vosslab-podcast`, then preserve the rule in architecture and validation documentation.
- If it is not adopted, remove it from the presentation/deployment change before integration.
- Verify accepted and rejected post shapes with focused deterministic tests, without making live
  publication depend on a cosmetic deployment change.

**Owner.** The cross-repository publication contract, with `vosslab-podcast` as producer owner and
this repository as independent validator.

## Priority 3: Remove the deployment/recovery import cycle

[scripts/site_deployment.py](../scripts/site_deployment.py) imports
[scripts/publication_transaction.py](../scripts/publication_transaction.py) inside `publish_site`,
while the transaction module imports the deployment module to decide whether a derived release serves
a bundle. The deferred import avoids an initialization failure but leaves transaction ownership split.

- Extract the shared lock and served-release receipt predicates into a neutral publisher-runtime
  module with one-directional imports.
- Keep bundle staging and commit recovery in the transaction module; keep presentation source
  validation, identity, and promotion in the deployment module.
- Give build callbacks an explicit callable type while consolidating the shared build mechanism.
- Verify importer idempotency, interrupted-transaction recovery, presentation idempotency, and
  failed-build preservation after the dependency boundary changes.

**Owner.** Publisher runtime architecture.

## Intentionally not started

- New bundle schemas, evidence formats, generation behavior, Git evidence collection, model
  execution, and scheduling remain owned by `vosslab-podcast`.
- Replacing the LAN static server or exposing the site to the public internet is outside the current
  private-network deployment scope.
