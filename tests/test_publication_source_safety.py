"""Test the standalone publication-source safety policy."""

# Standard Library
import hashlib

# PIP3 modules
import pytest

# local repo modules
import scripts.publication_source_safety


def post(body: str) -> str:
	"""Return a complete post with front matter that is irrelevant to this source policy."""
	value = "---\ntitle: Safe post\n---\n" + body
	return value


#============================================
def test_policy_identity_hashes_its_canonical_vector() -> None:
	"""The policy exposes a producer-shareable byte vector and matching digest."""
	identity = scripts.publication_source_safety.policy_identity()
	digest = hashlib.sha256(
		scripts.publication_source_safety.policy_vector_bytes()
	).hexdigest()
	assert identity["sha256"] == digest


#============================================
@pytest.mark.parametrize("case", scripts.publication_source_safety.POLICY_VECTOR["cases"])
def test_canonical_policy_vector_cases(case: dict) -> None:
	"""The fixed cross-repository vector is executable by this independent validator."""
	issues = scripts.publication_source_safety.validate_post_source(
		case["post"], scripts.publication_source_safety.POLICY_VECTOR["approved_paths"],
	)
	assert (not issues) is case["valid"]


#============================================
def test_accepts_allowed_markup_and_exact_evidence_comment() -> None:
	"""An approved asset and exact GitHub URL remain valid Markdown publication source."""
	source = post(
		"[source](https://github.com/vosslab/example)\n\n"
		"![shot](../../assets/publications/2026-08-30/shot.png)\n\n"
		"<!-- evidence: ev-0123456789abcdef, ev-fedcba9876543210 -->\n\n<!-- more -->\n"
	)
	issues = scripts.publication_source_safety.validate_post_source(
		source, ("../../assets/publications/2026-08-30/shot.png",),
	)
	assert issues == ()


#============================================
@pytest.mark.parametrize("body", (
	"<!-- note -->",
	"<!-- evidence: ev-ABCDEF0123456789 -->",
	"<script>alert(1)</script>",
	"<!DOCTYPE html>",
	"<?xml version='1.0'?>",
	"<![CDATA[not markdown]]>",
	"A heading {#unsafe}",
))
def test_rejects_active_html_and_attribute_syntax(body: str) -> None:
	"""Only the two documented active comment forms can enter a publication source."""
	issues = scripts.publication_source_safety.validate_post_source(post(body), ())
	assert issues


#============================================
@pytest.mark.parametrize("body", (
	'# Title { onclick="alert(1)" }',
	'Paragraph.\n{ data-state="active" }',
	'![proof](assets/proof.png){ .proof }',
	'[GitHub](https://github.com/vosslab/project){ #source }',
))
def test_rejects_spaced_attribute_lists(body: str) -> None:
	"""Each active attr_list form is rejected before publication."""
	issues = scripts.publication_source_safety.validate_post_source(
		post(body), ("assets/proof.png",),
	)
	assert "markdown_attribute_list" in issues


#============================================
def test_keeps_brace_prose_and_code_inert() -> None:
	"""Ordinary braces and code examples do not become active attributes."""
	assert scripts.publication_source_safety.validate_post_source(
		post('{a small set} ` { onclick="x" } `'), (),
	) == ()


#============================================
def test_code_spans_and_fences_are_inert() -> None:
	"""Code examples may document forbidden syntax without becoming executable source markup."""
	source = post(
		"`<script>bad</script> [bad](javascript:alert(1))`\n\n"
		"```html\n<!-- note -->\n<a href='bad'>x</a>\n```\n"
	)
	issues = scripts.publication_source_safety.validate_post_source(source, ())
	assert issues == ()


#============================================
@pytest.mark.parametrize("target", (
	"javascript:alert(1)",
	"//github.com/vosslab/example",
	"https://user@github.com/vosslab/example",
	"https://github.com:444/vosslab/example",
	"mailto:author@example.com",
	"https&#58;//evil.example/path",
))
def test_rejects_disguised_or_noncanonical_link_targets(target: str) -> None:
	"""URL normalization happens before the source policy makes its allow-list decision."""
	issues = scripts.publication_source_safety.validate_post_source(post(f"[bad]({target})"), ())
	assert issues


#============================================
def test_validates_unused_reference_definitions() -> None:
	"""A disallowed reference cannot hide in a source file merely because it is unused today."""
	issues = scripts.publication_source_safety.validate_post_source(
		post("[unused]: https://evil.example/path\n"), (),
	)
	assert "unsafe_link" in issues
