"""Publisher-side narrative evidence policy tests."""

# PIP3 modules
import pytest

# local repo modules
import scripts.validate_daily_post


#============================================
def validation_inputs() -> tuple[dict, dict, dict]:
	"""Return one minimum valid publisher validation packet."""
	evidence_id = "ev-maker-work"
	evidence = {"report_date": "2026-08-23", "items": []}
	projection = {
		"excerpts": [{"evidence_id": evidence_id, "kind": "dated_changelog"}],
	}
	bundle = {
		"report_date": "2026-08-23",
		"generator": {"run_id": "maker-run"},
		"contracts": {
			"prompt_version": scripts.validate_daily_post.V4_MAKER_POLICY.prompt_version,
			"rubric_version": scripts.validate_daily_post.V4_MAKER_POLICY.rubric_version,
			"candidate_validation": {
				"name": scripts.validate_daily_post.V4_MAKER_POLICY.name,
				"version": scripts.validate_daily_post.V4_MAKER_POLICY.version,
				"sha256": scripts.validate_daily_post.V4_MAKER_POLICY.digest,
			},
		},
	}
	return evidence, projection, bundle


#============================================
def post_with_body(body: str) -> str:
	"""Return a complete post that carries a supplied Markdown body."""
	post = (
		"---\n"
		"date: 2026-08-23\n"
		"slug: maker-work\n"
		"generator_run: maker-run\n"
		"evidence_manifest: evidence.json\n"
		"editorial_projection: editorial_projection.json\n"
		"---\n\n"
		+ body
	)
	return post


#============================================
def validate(body: str) -> list[str]:
	"""Validate one complete maker-post body against fixed evidence."""
	evidence, projection, bundle = validation_inputs()
	filler = " ".join(["maker"] * 310) + " <!-- evidence: ev-maker-work -->\n\n"
	if "## Project coverage" in body:
		body = body.replace("## Project coverage", filler + "## Project coverage", 1)
	else:
		body += "\n\n" + filler + "## Project coverage\n\nAlpha shipped its focused change.\n"
	issues = scripts.validate_daily_post.validate_post(
		post_with_body(body),
		evidence,
		projection,
		bundle,
		policy=scripts.validate_daily_post.V4_MAKER_POLICY,
	)
	return issues


#============================================
def cited_opening() -> str:
	"""Return an evidenced opening that satisfies first-person post requirements."""
	opening = (
		"# Making a smaller boundary\n\n"
		"I connected the published post to its source evidence. "
		"<!-- evidence: ev-maker-work -->\n\n"
		"<!-- more -->\n\n"
	)
	return opening


#============================================
def test_evidenced_opening_allows_one_uncited_narrative_block() -> None:
	"""An opening may pair one reflection with one cited factual block."""
	issues = validate(
		"# Making a smaller boundary\n\n"
		"I enjoyed finding the smaller shape of this validation boundary.\n\n"
		"I connected the published post to its source evidence. "
		"<!-- evidence: ev-maker-work -->\n\n"
		"<!-- more -->\n\n"
		"## Project coverage\n\n"
		"Alpha shipped its focused change.\n"
	)

	assert not issues


#============================================
def test_standalone_evidence_comment_evidences_its_narrative_section() -> None:
	"""A provenance comment can sit beside rather than inside the prose block."""
	issues = validate(
		"# Making a smaller boundary\n\n"
		"I enjoyed finding the smaller shape of this validation boundary.\n\n"
		"<!-- evidence: ev-maker-work -->\n\n"
		"<!-- more -->\n\n"
		"## Project coverage\n\n"
		"Alpha shipped its focused change.\n"
	)

	assert not issues


#============================================
def test_three_uncited_narrative_blocks_pass() -> None:
	"""The structural allowance accepts exactly three uncited prose blocks."""
	issues = validate(
		"# Making a smaller boundary\n\n"
		"I enjoyed finding the smaller shape of this validation boundary.\n\n"
		"I was surprised by how much room that gave the story.\n\n"
		"I learned that evidence can support a paragraph without owning every sentence.\n\n"
		"I connected the published post to its source evidence. "
		"<!-- evidence: ev-maker-work -->\n\n"
		"<!-- more -->\n\n"
		"## Project coverage\n\n"
		"Alpha shipped its focused change.\n"
	)

	assert not issues


#============================================
def test_four_uncited_narrative_blocks_fail() -> None:
	"""The fourth uncited narrative block exceeds the structural allowance."""
	issues = validate(
		"# Making a smaller boundary\n\n"
		"I enjoyed finding the smaller shape of this validation boundary.\n\n"
		"I was surprised by how much room that gave the story.\n\n"
		"I learned that evidence can support a paragraph without owning every sentence.\n\n"
		"I want to try the same approach on tomorrow's work.\n\n"
		"I connected the published post to its source evidence. "
		"<!-- evidence: ev-maker-work -->\n\n"
		"<!-- more -->\n\n"
		"## Project coverage\n\n"
		"Alpha shipped its focused change.\n"
	)

	assert "post contains too many uncited narrative prose blocks" in issues


#============================================
def test_final_project_coverage_is_excluded_from_uncited_block_cap() -> None:
	"""Compact final coverage does not consume the narrative allowance."""
	issues = validate(
		cited_opening()
		+ "## Project coverage\n\n"
		+ "Alpha shipped its focused change; Beta retained its small note; "
		+ "Gamma kept its compact summary; Delta remains outside the narrative allowance.\n"
	)

	assert not issues


#============================================
def test_nonfinal_project_coverage_leaves_afterword_in_narrative() -> None:
	"""An Afterword remains validated when coverage is not the final H2 footer."""
	issues = validate(
		cited_opening()
		+ "## Project coverage\n\n"
		+ "Alpha shipped its focused change. <!-- evidence: ev-maker-work -->\n\n"
		+ "## Afterword\n\n"
		+ "I still want to test one more shape tomorrow.\n"
	)

	assert "every narrative prose section must cite packet evidence" in issues


#============================================
def v3_post() -> str:
	"""Return a direct-validation post satisfying the historical policy."""
	paragraph = "I " + " ".join(["evidence"] * 180) + " <!-- evidence: ev-maker-work -->"
	body = (
		"# Making the boundary durable\n\n"
		+ paragraph
		+ "\n\n<!-- more -->\n\n## First pass\n\n"
		+ paragraph
		+ "\n\n## Second pass\n\n"
		+ paragraph
		+ "\n\n## Project coverage\n\n"
		+ "Alpha remains covered. <!-- evidence: ev-maker-work -->\n"
	)
	return post_with_body(body)


#============================================
def v3_bundle() -> dict:
	"""Return the exact active historical bundle policy identity."""
	policy = scripts.validate_daily_post.V3_HISTORICAL_POLICY
	return {
		"report_date": "2026-08-23",
		"generator": {"run_id": "maker-run"},
		"contracts": {
			"prompt_version": policy.prompt_version,
			"rubric_version": policy.rubric_version,
			"candidate_validation": {
				"name": policy.name,
				"version": policy.version,
				"sha256": policy.digest,
			},
		},
	}


#============================================
def test_direct_validation_defaults_to_exact_v3_historical_policy() -> None:
	"""No-policy direct validation admits only the active v3 contract."""
	evidence, projection, _unused = validation_inputs()
	issues = scripts.validate_daily_post.validate_post(v3_post(), evidence, projection, v3_bundle())

	assert not issues


#============================================
def test_direct_v3_aug_26_fixture_passes() -> None:
	"""The historical direct path retains a complete Aug. 26-shaped fixture."""
	evidence, projection, _unused = validation_inputs()
	bundle = v3_bundle()
	bundle["report_date"] = "2026-08-26"
	evidence["report_date"] = "2026-08-26"
	issues = scripts.validate_daily_post.validate_post(
		v3_post().replace("2026-08-23", "2026-08-26"), evidence, projection, bundle
	)

	assert not issues


#============================================
def test_v3_policy_allows_an_evidenced_afterword() -> None:
	"""The historical variant does not turn a later H2 into a v4-only rejection."""
	evidence, projection, _unused = validation_inputs()
	post = v3_post().replace(
		"Alpha remains covered. <!-- evidence: ev-maker-work -->\n",
		"Alpha remains covered. <!-- evidence: ev-maker-work -->\n\n"
		"## Afterword\n\nI kept one final note. <!-- evidence: ev-maker-work -->\n",
	)
	issues = scripts.validate_daily_post.validate_post(post, evidence, projection, v3_bundle())

	assert not issues


#============================================
@pytest.mark.parametrize(
	"afterword",
	(
		"### Quiet afterword\n\nI kept one final note.",
		"#### Quiet afterword\n\nI kept one final note.",
		"### Quiet afterword\nI kept one final note.",
		"<h3>Quiet afterword</h3>\n\nI kept one final note.",
	),
)
def test_v4_rejects_heading_after_compact_project_coverage(afterword: str) -> None:
	"""Maker coverage cannot hide an afterword behind a lower Markdown heading."""
	issues = validate(
		cited_opening()
		+ "## Project coverage\n\nAlpha shipped its focused change.\n\n"
		+ afterword
	)

	assert "Project coverage must not contain a later heading or afterword" in issues


#============================================
@pytest.mark.parametrize(
	("source", "expected"),
	(
		("[four readable words here](https://example.test/a/b/c \"hidden title\")", 4),
		("![hidden alt words](assets/image.png \"hidden title\") visible words", 2),
		("`hidden code words` visible words <!-- hidden comment words -->", 2),
		("[one two](https://example.test) [three four](https://example.test)", 4),
		("```text\nhidden fenced words\n```\nvisible words", 2),
		("<span title=\"hidden attribute\">visible words</span>", 2),
		("[hidden reference]: https://example.test/hidden\nvisible words", 2),
	),
)
def test_visible_word_count_matches_reader_visible_markdown(source: str, expected: int) -> None:
	"""Publisher word budgets match producer-visible Markdown rather than source bytes."""
	assert scripts.validate_daily_post.visible_word_count(source) == expected


#============================================
@pytest.mark.parametrize("limit", (350, 650, 300, 2500))
def test_visible_word_count_preserves_exact_policy_boundaries(limit: int) -> None:
	"""Long link destinations cannot inflate exact narrative and coverage boundaries."""
	words = " ".join(["word"] * (limit - 4))
	source = words + " [one two three four](https://example.test/" + ("x/" * 100) + ")"

	assert scripts.validate_daily_post.visible_word_count(source) == limit


#============================================
def test_optional_project_coverage_rule_gates_all_coverage_checks() -> None:
	"""The serialized coverage flag controls validation instead of being dead metadata."""
	rules = dict(scripts.validate_daily_post.V4_MAKER_POLICY.rules)
	rules["require_final_project_coverage"] = False
	policy = scripts.validate_daily_post._registered_policy(
		"coverage-optional",
		"v1",
		"daily-blog-prompts-v4",
		"daily-blog-rubric-v4",
		rules,
	)
	body = "I " + " ".join(["made"] * 310) + " <!-- evidence: ev-maker-work -->"
	issues = scripts.validate_daily_post._v4_shape_issues(
		body,
		{"repositories": [{"repository": "vosslab/alpha", "repository_url": ""}]},
		{"ev-maker-work"},
		policy,
	)

	assert not issues


#============================================
@pytest.mark.parametrize(
	("narrative", "expected"),
	(
		(
			"<span title=\"vosslab/alpha\">visible</span>\n\n"
			"[vosslab/alpha]: https://example.test/hidden\n\n"
			"[vosslab/alpha](https://github.com/vosslab/alpha)",
			True,
		),
		(
			"<!-- vosslab/alpha -->\n\n```text\nvosslab/alpha\n```\n\n"
			"`vosslab/alpha` [vosslab/alpha](https://github.com/vosslab/alpha)",
			True,
		),
		(
			"![vosslab/alpha](assets/image.png \"hidden\") "
			"[vosslab/alpha](https://github.com/vosslab/alpha)",
			True,
		),
		(
			"I mentioned vosslab/alpha before "
			"[vosslab/alpha](https://github.com/vosslab/alpha)",
			False,
		),
	),
)
def test_first_repository_link_uses_only_visible_markdown(
	narrative: str,
	expected: bool,
) -> None:
	"""Hidden source mentions do not preempt an actual first visible repository link."""
	assert scripts.validate_daily_post._first_narrative_repository_link(
		narrative,
		"vosslab/alpha",
		"https://github.com/vosslab/alpha",
	) is expected


#============================================
@pytest.mark.parametrize("limit", (350, 650))
def test_v3_word_budget_excludes_heading_words(limit: int) -> None:
	"""Historical narrative budgets count prose, never decorative H1 or H2 labels."""
	prose = " ".join(["word"] * limit) + " <!-- evidence: ev-maker-work -->"
	body = (
		"# Many heading words that must not count toward the historical budget\n\n"
		+ prose
		+ "\n\n<!-- more -->\n\n"
		+ "## Another heading whose words also do not count\n\n"
		+ "## A second heading that keeps the v3 section shape\n\n"
		+ "## Project coverage\n\n"
		+ "Alpha remains covered. <!-- evidence: ev-maker-work -->\n"
	)
	issues = scripts.validate_daily_post._v3_shape_issues(
		body,
		{"repositories": []},
		{"ev-maker-work"},
		scripts.validate_daily_post.V3_HISTORICAL_POLICY,
	)

	assert "post narrative must contain 350 through 650 visible words" not in issues


#============================================
def test_direct_v4_requires_explicit_registered_policy() -> None:
	"""The future maker policy cannot become active through bundle metadata alone."""
	evidence, projection, bundle = validation_inputs()
	with pytest.raises(RuntimeError, match="unsupported"):
		scripts.validate_daily_post.validate_post(post_with_body(cited_opening()), evidence, projection, bundle)


#============================================
def test_policy_tuple_and_caller_built_policy_are_rejected() -> None:
	"""The publisher accepts neither digest tampering nor lookalike policy objects."""
	evidence, projection, bundle = validation_inputs()
	bundle["contracts"]["candidate_validation"]["sha256"] = "0" * 64
	with pytest.raises(RuntimeError, match="unsupported"):
		scripts.validate_daily_post.validate_post(
			post_with_body(cited_opening()), evidence, projection, bundle,
			policy=scripts.validate_daily_post.V4_MAKER_POLICY,
		)
	lookalike = scripts.validate_daily_post.PostValidationPolicy(
		name="v4-maker",
		version="v1",
		prompt_version="daily-blog-prompts-v4",
		rubric_version="daily-blog-rubric-v4",
		rules=scripts.validate_daily_post.V4_MAKER_POLICY.rules,
		digest=scripts.validate_daily_post.V4_MAKER_POLICY.digest,
	)
	with pytest.raises(RuntimeError, match="registered"):
		scripts.validate_daily_post.validate_post(
			post_with_body(cited_opening()), evidence, projection, validation_inputs()[2],
			policy=lookalike,
		)


#============================================
def test_policy_digests_bind_the_complete_declared_rule_set() -> None:
	"""A policy digest changes when a behavior-affecting rule changes."""
	policy = scripts.validate_daily_post.V4_MAKER_POLICY
	assert policy.digest == "1bbca12465f37c32d5c0dc728b45633bf9969d21532467b7abe7584902505bb1"
	assert scripts.validate_daily_post.V3_HISTORICAL_POLICY.digest == (
		"e1df6f1a9bea8b6459a15140669e726320a99e411ad1a4677aa5c555ca7fbe0f"
	)
	changed_rules = dict(policy.rules)
	changed_rules["max_uncited_narrative_blocks"] = 4
	changed = scripts.validate_daily_post._policy_digest(
		policy.name,
		policy.version,
		tuple(sorted(changed_rules.items())),
	)

	assert policy.digest != changed
	invalid_rules = dict(scripts.validate_daily_post.V3_HISTORICAL_POLICY.rules)
	invalid_rules["max_uncited_narrative_blocks"] = None
	with pytest.raises(RuntimeError, match="nonnegative integers"):
		scripts.validate_daily_post._registered_policy(
			"invalid-policy",
			"v1",
			"daily-blog-prompts-v3",
			"daily-blog-rubric-v3",
			invalid_rules,
		)
