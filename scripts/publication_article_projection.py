"""Bind a published reader article to the staged Markdown post body."""

# Standard Library
import hashlib
import html
from html.parser import HTMLParser
import os
import re

# PIP3 modules
import markdown
import yaml


ARTICLE_CLASS_TOKENS = frozenset({"md-content__inner", "md-typeset"})
WHITESPACE_RE = re.compile(r"\s+")
HIDDEN_STYLE_RE = re.compile(r"(?:display\s*:\s*none|visibility\s*:\s*hidden)", re.I)
PERMALINK_CLASS = "headerlink"
VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})


#============================================
def _normalized_text(value: str) -> str:
	"""Return one whitespace-stable reader-visible text value."""
	plain = html.unescape(value)
	normalized = WHITESPACE_RE.sub(" ", plain).strip()
	return normalized


#============================================
def _attributes(pairs: list[tuple[str, str | None]]) -> dict[str, str]:
	"""Return lower-case HTML attributes without absent values."""
	attributes = {}
	for name, value in pairs:
		if value is not None:
			attributes[name.lower()] = value
	return attributes


#============================================
def _is_hidden(attributes: dict[str, str]) -> bool:
	"""Return whether an element and its descendants are reader-hidden."""
	if "hidden" in attributes or attributes.get("aria-hidden", "").lower() == "true":
		return True
	classes = set(attributes.get("class", "").split())
	if "hidden" in classes or "visually-hidden" in classes:
		return True
	value = attributes.get("style", "")
	hidden = HIDDEN_STYLE_RE.search(value) is not None
	return hidden


#============================================
class _ProjectionParser(HTMLParser):
	"""Collect canonical visible reader tokens from an HTML fragment."""
	def __init__(self) -> None:
		super().__init__(convert_charrefs=True)
		self.tokens: list[str] = []
		self._hidden_depth = 0
		self._suppressed_depth = 0
		self._code_depth = 0
		self._stack: list[tuple[bool, bool, bool]] = []

	def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
		"""Track nested visibility states before accepting this element's text."""
		attributes = _attributes(attrs)
		classes = set(attributes.get("class", "").split())
		# A descendant stays hidden or suppressed while its ancestor's depth is open.
		hidden = self._hidden_depth > 0 or _is_hidden(attributes)
		suppressed = self._suppressed_depth > 0 or tag in {"script", "style"}
		permalink = tag == "a" and PERMALINK_CLASS in classes
		# The stack mirrors non-void nesting so closing tags can unwind each state exactly.
		if tag not in VOID_TAGS:
			self._stack.append((hidden, suppressed or permalink, tag in {"code", "pre"}))
		if hidden:
			self._hidden_depth += 1
		if suppressed or permalink:
			self._suppressed_depth += 1
		if tag in {"code", "pre"}:
			self._code_depth += 1
		# Image alt text is the reader-visible representation when the element is eligible.
		if tag == "img" and not hidden and not suppressed:
			alt = _normalized_text(attributes.get("alt", ""))
			self.tokens.append(f"image:{alt}")

	def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
		"""Apply the same state transition for an explicitly self-closing element."""
		self.handle_starttag(tag, attrs)
		if tag not in VOID_TAGS:
			self.handle_endtag(tag)

	def handle_endtag(self, _tag: str) -> None:
		"""Unwind the visibility, suppression, and code depths for one open element."""
		if not self._stack:
			raise RuntimeError("Rendered article HTML is structurally invalid.")
		hidden, suppressed, code = self._stack.pop()
		if hidden:
			self._hidden_depth -= 1
		if suppressed:
			self._suppressed_depth -= 1
		if code:
			self._code_depth -= 1

	def handle_data(self, data: str) -> None:
		"""Emit normalized text only from the currently visible reader surface."""
		if self._hidden_depth or self._suppressed_depth:
			return
		text = _normalized_text(data)
		if not text:
			return
		prefix = "code" if self._code_depth else "text"
		self.tokens.append(f"{prefix}:{text}")

	def projection(self) -> str:
		"""Return the ordered token projection and reject malformed fragments."""
		if self._stack:
			raise RuntimeError("Rendered article HTML is structurally incomplete.")
		projection = "\n".join(self.tokens)
		return projection


#============================================
def _post_body(markdown_post: str) -> str:
	"""Return one Markdown post body after its required front matter."""
	if not markdown_post.startswith("---\n"):
		raise RuntimeError("Publication post must begin with front matter.")
	closing = markdown_post.find("\n---\n", len("---\n"))
	if closing < 0:
		raise RuntimeError("Publication post front matter is incomplete.")
	body = markdown_post[closing + len("\n---\n"):]
	if not body.strip():
		raise RuntimeError("Publication post body is empty.")
	return body


#============================================
def _markdown_extensions(config_path: str) -> tuple[list[str], dict[str, object]]:
	"""Load the staged MkDocs Markdown extension declarations exactly."""
	with open(config_path, encoding="utf-8") as handle:
		config = yaml.safe_load(handle)
	if not isinstance(config, dict):
		raise RuntimeError("Staged MkDocs configuration must be one mapping.")
	declared = config.get("markdown_extensions", [])
	if not isinstance(declared, list):
		raise RuntimeError("MkDocs markdown_extensions must be a list.")
	extensions = []
	extension_configs = {}
	for item in declared:
		if isinstance(item, str):
			extensions.append(item)
			continue
		if not isinstance(item, dict) or len(item) != 1:
			raise RuntimeError("MkDocs markdown extension declaration is invalid.")
		name, options = next(iter(item.items()))
		if not isinstance(name, str) or not isinstance(options, dict):
			raise RuntimeError("MkDocs markdown extension declaration is invalid.")
		extensions.append(name)
		extension_configs[name] = options
	return extensions, extension_configs


#============================================
def render_staged_post_body(markdown_post: str, config_path: str) -> str:
	"""Render the staged post body with its staged MkDocs extensions."""
	body = _post_body(markdown_post)
	extensions, extension_configs = _markdown_extensions(config_path)
	renderer = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
	rendered = renderer.convert(body)
	return rendered


#============================================
def source_article_projection(markdown_post: str, config_path: str) -> str:
	"""Render the staged post body and return its canonical reader projection."""
	rendered = render_staged_post_body(markdown_post, config_path)
	parser = _ProjectionParser()
	parser.feed(rendered)
	parser.close()
	projection = parser.projection()
	if not projection:
		raise RuntimeError("Publication post has no reader-visible body projection.")
	return projection


#============================================
def article_body_sha256(projection: str) -> str:
	"""Return the receipt digest for one canonical reader projection."""
	if not projection:
		raise RuntimeError("Publication article projection is empty.")
	digest = hashlib.sha256(projection.encode("utf-8")).hexdigest()
	return digest


#============================================
class _ArticleParser(HTMLParser):
	"""Extract canonical tokens from exactly one Material article surface."""
	def __init__(self) -> None:
		super().__init__(convert_charrefs=True)
		self._candidates: list[_ProjectionParser] = []
		self._active: list[tuple[int, _ProjectionParser]] = []
		self._depth = 0

	def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
		"""Forward descendants into each active Material article candidate."""
		# Existing candidates see this tag before a newly opened article begins collecting.
		for _start_depth, parser in self._active:
			parser.handle_starttag(tag, attrs)
		if tag in VOID_TAGS:
			return
		self._depth += 1
		attributes = _attributes(attrs)
		classes = set(attributes.get("class", "").split())
		if tag == "article" and ARTICLE_CLASS_TOKENS <= classes:
			# Save the article depth so its own closing tag is not forwarded into its body.
			parser = _ProjectionParser()
			self._candidates.append(parser)
			self._active.append((self._depth, parser))

	def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
		"""Forward a self-closing element without changing persistent page depth."""
		self.handle_starttag(tag, attrs)
		if tag not in VOID_TAGS:
			self.handle_endtag(tag)

	def handle_endtag(self, tag: str) -> None:
		"""Forward nested closing tags, then retire articles closing at this depth."""
		# Only descendants close inside a candidate; its outer article tag is structural.
		for start_depth, parser in self._active:
			if start_depth < self._depth:
				parser.handle_endtag(tag)
		active = []
		for start_depth, parser in self._active:
			if start_depth != self._depth:
				active.append((start_depth, parser))
		self._active = active
		self._depth -= 1

	def handle_data(self, data: str) -> None:
		"""Forward text into every article that encloses the current page position."""
		for _start_depth, parser in self._active:
			parser.handle_data(data)

	def projections(self) -> list[str]:
		if self._active or self._depth:
			raise RuntimeError("Built page HTML is structurally incomplete.")
		projections = [candidate.projection() for candidate in self._candidates]
		return projections


#============================================
def _contains_projection(actual: str, expected: str) -> bool:
	"""Return whether every source token appears in reader order."""
	actual_tokens = actual.splitlines()
	expected_tokens = expected.splitlines()
	position = 0
	for expected_token in expected_tokens:
		while position < len(actual_tokens) and actual_tokens[position] != expected_token:
			position += 1
		if position == len(actual_tokens):
			return False
		position += 1
	return True


#============================================
def _asset_semantic_path(path: str) -> str:
	"""Normalize a rendered or source image path to its immutable asset suffix."""
	marker = "/assets/"
	index = path.find(marker)
	if index < 0:
		raise RuntimeError("Built article image is outside the publication assets namespace.")
	return path[index:]


#============================================
def verify_built_article(
	site_dir: str,
	report_date: str,
	expected_projection: str,
	allowed_image_paths: set[str] | None = None,
) -> None:
	"""Require one dated built article to retain the complete source projection."""
	if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report_date):
		raise RuntimeError("Publication report date is invalid for article verification.")
	matches = []
	for current_root, _directories, names in os.walk(site_dir):
		for name in sorted(names):
			if name != "index.html":
				continue
			path = os.path.join(current_root, name)
			with open(path, encoding="utf-8") as handle:
				page = handle.read()
			date_pattern = (
				rf"<time\b[^>]*\bdatetime=[\"']{re.escape(report_date)}"
				rf"(?:[ T][^\"']*)?[\"']"
			)
			if re.search(date_pattern, page) is None:
				continue
			parser = _ArticleParser()
			parser.feed(page)
			parser.close()
			projections = parser.projections()
			matching = [
				value for value in projections if _contains_projection(value, expected_projection)
			]
			if matching:
				if len(projections) != 1:
					raise RuntimeError("Dated built page has an ambiguous reader article surface.")
				if allowed_image_paths is not None:
					# ASVS 2.3.3: verify the rendered article preserves the sealed image scope.
					article_match = re.search(
						r"<article\b[^>]*\bmd-content__inner\b[^>]*>(.*?)</article>",
						page, re.DOTALL,
					)
					if article_match is None:
						raise RuntimeError("Built dated page has no reader article image surface.")
					image_paths = set(re.findall(
						r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", article_match.group(1),
					))
					allowed_paths = {_asset_semantic_path(path) for path in allowed_image_paths}
					if {_asset_semantic_path(path) for path in image_paths} - allowed_paths:
						raise RuntimeError("Built article embeds an image outside its publication surface.")
				matches.append(path)
	if len(matches) != 1:
		raise RuntimeError("Built dated reader article does not retain the staged post body.")
