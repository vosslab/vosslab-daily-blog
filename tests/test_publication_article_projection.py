"""Reader-body provenance checks for publication staging."""

# Standard Library
import pathlib

# PIP3 modules
import pytest

# local repo modules
import scripts.publication_article_projection


REPORT_DATE = "2026-08-23"


#============================================
def _config(path: pathlib.Path) -> str:
	"""Write the small staged Markdown configuration used by these checks."""
	path.write_text("markdown_extensions:\n  - toc:\n      permalink: true\n", encoding="utf-8")
	return str(path)


#============================================
def _post(body: str) -> str:
	"""Return a complete selected-post input with one reader body."""
	post = "---\ndate: 2026-08-23\nslug: projection\n---\n\n" + body
	return post


#============================================
def test_source_projection_includes_visible_code_and_image_alt(tmp_path: pathlib.Path) -> None:
	"""The receipt commits visible prose, code, and an image's accessible name."""
	projection = scripts.publication_article_projection.source_article_projection(
		_post("# Title\n\nVisible `code` text.\n\n![Diagram alt](diagram.png)"),
		_config(tmp_path / "mkdocs.yml"),
	)

	assert "code:code" in projection and "image:Diagram alt" in projection


#============================================
def test_built_article_allows_chrome_but_rejects_wrong_body(tmp_path: pathlib.Path) -> None:
	"""Permalink chrome survives while a same-date wrong article is rejected."""
	config_path = _config(tmp_path / "mkdocs.yml")
	expected = scripts.publication_article_projection.source_article_projection(
		_post(
			"# Kept heading\n\nGrounded reader body.\n\n"
			"![Selected proof](../../assets/publications/2026-08-23/proof.png)"
		), config_path
	)
	site_dir = tmp_path / "site"
	site_dir.mkdir()
	page = site_dir / "index.html"
	page.write_text(
		'<time datetime="2026-08-23 00:00:00+00:00"></time>'
		'<article class="md-content__inner md-typeset"><h1>Kept heading'
		'<a class="headerlink">#</a></h1><p>Grounded reader body.</p>'
		'<img alt="Selected proof" src="../../../assets/publications/2026-08-23/proof.png"></article>',
		encoding="utf-8",
	)
	scripts.publication_article_projection.verify_built_article(
		str(site_dir), REPORT_DATE, expected,
		{"../../assets/publications/2026-08-23/proof.png"},
	)
	page.write_text(
		'<time datetime="2026-08-23 00:00:00+00:00"></time>'
		'<article class="md-content__inner md-typeset"><h1>Kept heading</h1>'
		'<p>Wrong body.</p></article>',
		encoding="utf-8",
	)

	with pytest.raises(RuntimeError, match="does not retain"):
		scripts.publication_article_projection.verify_built_article(
			str(site_dir), REPORT_DATE, expected
		)


#============================================
def test_built_article_rejects_empty_same_date_article(tmp_path: pathlib.Path) -> None:
	"""A dated shell cannot stand in for a staged reader body."""
	config_path = _config(tmp_path / "mkdocs.yml")
	expected = scripts.publication_article_projection.source_article_projection(
		_post("# Kept heading\n\nGrounded reader body."), config_path
	)
	site_dir = tmp_path / "site"
	site_dir.mkdir()
	(site_dir / "index.html").write_text(
		'<time datetime="2026-08-23 00:00:00+00:00"></time>'
		'<article class="md-content__inner md-typeset"></article>',
		encoding="utf-8",
	)

	with pytest.raises(RuntimeError, match="does not retain"):
		 scripts.publication_article_projection.verify_built_article(
			str(site_dir), REPORT_DATE, expected
		)


#============================================
def test_built_article_rejects_unselected_article_image(tmp_path: pathlib.Path) -> None:
	"""A rendered article cannot widen its sealed image scope after staging."""
	config_path = _config(tmp_path / "mkdocs.yml")
	selected_path = "../../assets/publications/2026-08-23/selected.png"
	expected = scripts.publication_article_projection.source_article_projection(
		_post(f"# Kept heading\n\nGrounded reader body.\n\n![Selected]({selected_path})"),
		config_path,
	)
	site_dir = tmp_path / "site"
	site_dir.mkdir()
	(site_dir / "index.html").write_text(
		'<time datetime="2026-08-23 00:00:00+00:00"></time>'
		'<article class="md-content__inner md-typeset"><h1>Kept heading</h1>'
		'<p>Grounded reader body.</p>'
		'<img alt="Selected" src="../../../assets/publications/2026-08-23/selected.png">'
		'<img alt="Unselected" src="../../../assets/publications/2026-08-23/unselected.png"></article>',
		encoding="utf-8",
	)

	with pytest.raises(RuntimeError, match="outside its publication surface"):
		scripts.publication_article_projection.verify_built_article(
			str(site_dir), REPORT_DATE, expected, {selected_path},
		)
