"""Publisher-side narrative evidence policy tests."""

# PIP3 modules
import pytest

# local repo modules
import scripts.validate_daily_post


#============================================
def validation_inputs() -> tuple[dict, dict, dict]:
	"""Return one minimum valid publisher validation packet."""
	evidence_id = "ev-maker-work"
	evidence = {
		"report_date": "2026-08-23",
		"activity": [{"repository": "Alpha"}],
		"items": [],
	}
	projection = {
		"excerpts": [{"evidence_id": evidence_id, "kind": "dated_changelog"}],
		"repositories": [{"repository": "Alpha", "repository_url": ""}],
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
		"I connected the published post to its source evidence. "
		"<!-- evidence: ev-maker-work -->\n\n"
		"<!-- more -->\n\n"
		"I enjoyed finding the smaller shape of this validation boundary.\n\n"
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
		"I connected the published post to its source evidence. "
		"<!-- evidence: ev-maker-work -->\n\n"
		"<!-- more -->\n\n"
		"I enjoyed finding the smaller shape of this validation boundary.\n\n"
		"I was surprised by how much room that gave the story.\n\n"
		"I learned that evidence can support a paragraph without owning every sentence.\n\n"
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
	opening = "I " + " ".join(["evidence"] * 80) + " <!-- evidence: ev-maker-work -->"
	paragraph = "I " + " ".join(["evidence"] * 180) + " <!-- evidence: ev-maker-work -->"
	body = (
		"# Making the boundary durable\n\n"
		+ opening
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
def test_v3_requires_project_coverage_as_the_final_h2() -> None:
	"""Historical coverage is final at H2 level while lower headings remain permitted."""
	evidence, projection, _unused = validation_inputs()
	post = v3_post().replace(
		"Alpha remains covered. <!-- evidence: ev-maker-work -->\n",
		"Alpha remains covered. <!-- evidence: ev-maker-work -->\n\n"
		"## Afterword\n\nI kept one final note. <!-- evidence: ev-maker-work -->\n",
	)
	issues = scripts.validate_daily_post.validate_post(post, evidence, projection, v3_bundle())

	assert "post must finish with one Project coverage H2 section" in issues


#============================================
def test_v3_allows_a_lower_heading_after_final_project_coverage() -> None:
	"""The historical afterword boundary does not reject lower H3 structure."""
	evidence, projection, _unused = validation_inputs()
	post = v3_post().replace(
		"Alpha remains covered. <!-- evidence: ev-maker-work -->\n",
		"Alpha remains covered. <!-- evidence: ev-maker-work -->\n\n"
		"### Quiet afterword\n\nI kept one final note. <!-- evidence: ev-maker-work -->\n",
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
	issues = scripts.validate_daily_post._shape_issues(
		body,
		{"activity": [{"repository": "vosslab/alpha"}]},
		{"repositories": [{"repository": "vosslab/alpha", "repository_url": ""}]},
		{"ev-maker-work"},
		policy,
	)

	assert not issues


#============================================
def test_shape_validator_combines_h2_bounds_with_paragraph_evidence() -> None:
	"""One policy can relax H2 shape while retaining paragraph-level evidence."""
	rules = dict(scripts.validate_daily_post.V3_HISTORICAL_POLICY.rules)
	rules["min_narrative_h2"] = 0
	rules["max_narrative_h2"] = 12
	policy = scripts.validate_daily_post._registered_policy(
		"combined-h2-paragraph", "v1", "prompt", "rubric", rules
	)
	body = (
		"I " + " ".join(["made"] * 350) + "\n\n"
		"## Project coverage\n\nAlpha remains covered. <!-- evidence: ev-maker-work -->\n"
	)
	issues = scripts.validate_daily_post._shape_issues(
		body,
		{"activity": [{"repository": "Alpha"}]},
		{"repositories": []},
		{"ev-maker-work"},
		policy,
	)

	assert "every factual prose paragraph must cite packet evidence" in issues
	assert "post must contain two through four narrative H2 sections" not in issues


#============================================
def test_shape_validator_applies_compact_coverage_without_a_policy_family() -> None:
	"""Coverage caps take effect when declared on an otherwise historical policy."""
	rules = dict(scripts.validate_daily_post.V3_HISTORICAL_POLICY.rules)
	rules["coverage_max_blocks"] = 1
	rules["coverage_max_words"] = 200
	policy = scripts.validate_daily_post._registered_policy(
		"combined-compact-coverage", "v1", "prompt", "rubric", rules
	)
	body = v3_post().split("---\n", 2)[2].replace(
		"Alpha remains covered. <!-- evidence: ev-maker-work -->\n",
		"Alpha remains covered. <!-- evidence: ev-maker-work -->\n\n"
		"Beta remains covered. <!-- evidence: ev-maker-work -->\n",
	)
	issues = scripts.validate_daily_post._shape_issues(
		body,
		{"activity": [{"repository": "Alpha"}, {"repository": "Beta"}]},
		{"repositories": []},
		{"ev-maker-work"},
		policy,
	)

	assert "Project coverage must use one compact paragraph or list" in issues


#============================================
def test_shape_validator_applies_declared_word_reader_model() -> None:
	"""Changing only word_count_mode changes the same shape decision."""
	rules = dict(scripts.validate_daily_post.V4_MAKER_POLICY.rules)
	rules["require_final_project_coverage"] = False
	rules["require_first_narrative_repository_link"] = False
	rules["require_section_evidence"] = False
	rules["min_narrative_words"] = 10
	rules["max_narrative_words"] = 10
	rules["word_count_mode"] = "legacy_source"
	legacy_policy = scripts.validate_daily_post._registered_policy(
		"combined-source-words", "v1", "prompt", "rubric", rules
	)
	body = "[one](https://example.test/two-three) <span title=\"four\">five</span>"
	inputs = ({"activity": []}, {"repositories": []}, set())
	legacy_issues = scripts.validate_daily_post._shape_issues(
		body, *inputs, legacy_policy
	)
	rules["word_count_mode"] = "reader_visible_markdown"
	visible_policy = scripts.validate_daily_post._registered_policy(
		"combined-visible-words", "v1", "prompt", "rubric", rules
	)
	visible_issues = scripts.validate_daily_post._shape_issues(
		body, *inputs, visible_policy
	)

	assert not legacy_issues
	assert "post narrative must contain 10 through 10 visible words" in visible_issues


#============================================
def test_shape_validator_enforces_zero_uncited_budget_without_paragraph_rule() -> None:
	"""An explicit zero allowance remains meaningful outside paragraph validation."""
	rules = dict(scripts.validate_daily_post.V4_MAKER_POLICY.rules)
	rules["require_final_project_coverage"] = False
	rules["require_first_narrative_repository_link"] = False
	rules["require_section_evidence"] = False
	rules["min_narrative_words"] = 0
	rules["max_uncited_narrative_blocks"] = 0
	policy = scripts.validate_daily_post._registered_policy(
		"combined-zero-uncited", "v1", "prompt", "rubric", rules
	)
	issues = scripts.validate_daily_post._shape_issues(
		"I kept one uncited maker note.", {"activity": []},
		{"repositories": []}, set(), policy,
	)

	assert "post contains too many uncited narrative prose blocks" in issues


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
	issues = scripts.validate_daily_post._shape_issues(
		body,
		{"activity": []},
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
	assert policy.digest == "3a4b7148579e509b6c32fa19b31d107dc4278eb5f721b2a01353a1a9a51264ee"
	assert scripts.validate_daily_post.V3_HISTORICAL_POLICY.digest == (
		"aada487814ca0080d4a49648440ee6614e5f3a3628be6197ffafcef242969324"
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


#============================================
def test_opening_policy_accepts_exact_pre_excerpt_boundaries() -> None:
	"""One short opening before one marker remains the exact valid shape."""
	post = post_with_body(
		"# Specific title\n\nI made a small boundary.\n\n<!-- more -->\n\n"
		"## Project coverage\n\nAlpha remains covered.\n"
	)
	front_matter, body = scripts.validate_daily_post.parse_front_matter(post)

	assert front_matter["slug"] == "maker-work"
	assert not scripts.validate_daily_post._opening_issues(
		post, body, scripts.validate_daily_post.V4_MAKER_POLICY
	)


#============================================
@pytest.mark.parametrize(
	("opening", "expected"),
	(
		("I made one note.\n\n<!-- more -->", None),
		("I made one note.\n\n<!-- more -->\n\n<!-- more -->", "excerpt marker"),
		("I made one note.\n\nI made another note.\n\n<!-- more -->", "one prose block"),
		("## Too early\n\nI made one note.\n\n<!-- more -->", "must not contain an H2"),
		(" ".join(["word"] * 101) + "\n\n<!-- more -->", "word budget"),
	),
)
def test_opening_policy_rejects_each_cross_boundary(
	opening: str,
	expected: str | None,
) -> None:
	"""Opening admission keeps marker, block, H2, and word limits independent."""
	body = "# Specific title\n\n" + opening + "\n\n## Project coverage\n\nAlpha remains covered."
	post = post_with_body(body)
	_unused, parsed_body = scripts.validate_daily_post.parse_front_matter(post)
	issues = scripts.validate_daily_post._opening_issues(
		post, parsed_body, scripts.validate_daily_post.V4_MAKER_POLICY
	)

	if expected is None:
		assert not issues
	else:
		assert any(expected in issue for issue in issues)


#============================================
def test_opening_policy_rejects_candidate_at_24001_characters() -> None:
	"""The maximum candidate length is enforced by the immutable policy field."""
	prefix = "# Specific title\n\n"
	suffix = "\n\n<!-- more -->\n\n## Project coverage\n"
	payload_size = 24001 - len(post_with_body(prefix + suffix))
	body = prefix + ("x" * payload_size) + suffix
	post = post_with_body(body)
	_unused, parsed_body = scripts.validate_daily_post.parse_front_matter(post)
	issues = scripts.validate_daily_post._opening_issues(
		post, parsed_body, scripts.validate_daily_post.V4_MAKER_POLICY
	)

	assert len(post) == 24001
	assert "post exceeds the candidate character budget" in issues


#============================================
@pytest.mark.parametrize(
	("rule", "value"),
	(
		("coverage_repository_scope", "unknown"),
		("coverage_repository_scope", 1),
		("word_count_mode", "unknown"),
		("word_count_mode", False),
	),
)
def test_registered_policy_rejects_invalid_enum_rules(rule: str, value: object) -> None:
	"""Every behavior enum must be present and belong to its closed vocabulary."""
	rules = dict(scripts.validate_daily_post.V4_MAKER_POLICY.rules)
	rules[rule] = value

	with pytest.raises(RuntimeError, match="enum rules"):
		scripts.validate_daily_post._registered_policy(
			"invalid-enum", "v2", "prompt", "rubric", rules
		)


#============================================
def test_registered_policy_rejects_missing_enum_rules() -> None:
	"""A policy digest cannot omit its coverage or reader-model behavior."""
	rules = dict(scripts.validate_daily_post.V4_MAKER_POLICY.rules)
	del rules["word_count_mode"]

	with pytest.raises(RuntimeError, match="incomplete"):
		scripts.validate_daily_post._registered_policy(
			"missing-enum", "v2", "prompt", "rubric", rules
		)


#============================================
@pytest.mark.parametrize(
	("rule", "value", "message"),
	(
		("max_candidate_chars", 0, "candidate character limit"),
		("required_excerpt_marker_count", -1, "nonnegative integers"),
		("required_opening_prose_blocks", "one", "nonnegative integers"),
		("max_opening_h2", False, "nonnegative integers"),
		("max_opening_words", -1, "nonnegative integers"),
	),
)
def test_registered_policy_rejects_malformed_opening_rules(
	rule: str,
	value: object,
	message: str,
) -> None:
	"""Every immutable opening field rejects malformed or unsafe policy records."""
	rules = dict(scripts.validate_daily_post.V4_MAKER_POLICY.rules)
	rules[rule] = value

	with pytest.raises(RuntimeError, match=message):
		scripts.validate_daily_post._registered_policy(
			"invalid-opening", "v3", "prompt", "rubric", rules
		)


#============================================
def test_registered_policy_rejects_opening_limits_without_one_marker() -> None:
	"""Opening constraints cannot survive an ambiguous excerpt-marker cardinality."""
	rules = dict(scripts.validate_daily_post.V4_MAKER_POLICY.rules)
	rules["required_excerpt_marker_count"] = 0

	with pytest.raises(RuntimeError, match="require one excerpt marker"):
		scripts.validate_daily_post._registered_policy(
			"invalid-marker", "v3", "prompt", "rubric", rules
		)


#============================================
def test_opening_policy_allows_zero_markers_only_with_zero_opening_limits() -> None:
	"""A non-opening policy does not attempt to parse a nonexistent excerpt marker."""
	rules = dict(scripts.validate_daily_post.V4_MAKER_POLICY.rules)
	rules["required_excerpt_marker_count"] = 0
	rules["required_opening_prose_blocks"] = 0
	rules["max_opening_h2"] = 0
	rules["max_opening_words"] = 0
	policy = scripts.validate_daily_post._registered_policy(
		"zero-marker", "v3", "prompt", "rubric", rules
	)
	post = post_with_body("# Specific title\n\nI made a small boundary.\n")
	_unused, body = scripts.validate_daily_post.parse_front_matter(post)

	assert not scripts.validate_daily_post._opening_issues(post, body, policy)


#============================================
def test_v3_uses_packet_activity_for_project_coverage() -> None:
	"""Historical coverage names every activity repository, not projection selection."""
	body = v3_post().replace("Alpha remains covered", "packet-alpha remains covered")
	issues = scripts.validate_daily_post._shape_issues(
		body.split("---\n", 2)[2],
		{"activity": [{"repository": "packet-alpha"}]},
		{"repositories": [{"repository": "projection-beta"}]},
		{"ev-maker-work"},
		scripts.validate_daily_post.V3_HISTORICAL_POLICY,
	)

	assert not issues


#============================================
def test_v4_uses_projected_repositories_for_project_coverage() -> None:
	"""Maker coverage names its editorial projection, not every packet activity row."""
	body = "I " + " ".join(["made"] * 300) + " <!-- evidence: ev-maker-work -->\n\n"
	body += "## Project coverage\n\nprojection-beta remains covered.\n"
	issues = scripts.validate_daily_post._shape_issues(
		body,
		{"activity": [{"repository": "packet-alpha"}]},
		{"repositories": [{"repository": "projection-beta", "repository_url": ""}]},
		{"ev-maker-work"},
		scripts.validate_daily_post.V4_MAKER_POLICY,
	)

	assert not issues


#============================================
def test_v3_counts_historical_markdown_source() -> None:
	"""Historical budgets retain link destinations and raw tags from source Markdown."""
	source = "[one](https://example.test/two-three) <span title=\"four\">five</span>"

	assert scripts.validate_daily_post.policy_word_count(
		source, scripts.validate_daily_post.V3_HISTORICAL_POLICY
	) == 10


#============================================
def test_v4_counts_only_reader_visible_markdown() -> None:
	"""Maker budgets exclude link targets and raw HTML attributes."""
	source = "[one](https://example.test/two-three) <span title=\"four\">five</span>"

	assert scripts.validate_daily_post.policy_word_count(
		source, scripts.validate_daily_post.V4_MAKER_POLICY
	) == 2


#============================================
@pytest.mark.parametrize(
	("title", "expected"),
	(
		("Work log", True),
		("Daily work log for 2026-08-23", True),
		("2026-08-23 daily work log", True),
		("Work log on August 23 2026", False),
		("Making the receipt boundary legible", False),
	),
)
def test_generic_work_log_title_matches_producer_normalization(
	title: str,
	expected: bool,
) -> None:
	"""Publisher title normalization matches the producer's closed generic-title set."""
	body = "# " + title + "\n"

	assert scripts.validate_daily_post.generic_work_log_title(body, "2026-08-23") is expected


#============================================
@pytest.mark.parametrize("evidence", ({}, {"activity": [{}]}, {"activity": ["alpha"]}))
def test_malformed_coverage_scope_fails_closed(evidence: dict) -> None:
	"""Coverage validation does not silently omit malformed policy-selected names."""
	issues = scripts.validate_daily_post._shape_issues(
		v3_post().split("---\n", 2)[2],
		evidence,
		{"repositories": []},
		{"ev-maker-work"},
		scripts.validate_daily_post.V3_HISTORICAL_POLICY,
	)

	assert "Project coverage repository scope is malformed" in issues
