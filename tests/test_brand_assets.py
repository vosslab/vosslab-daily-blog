# Standard Library
import os
import xml.etree.ElementTree as ET

# PIP3 modules
import yaml

# local repo modules
import file_utils

REPO_ROOT = file_utils.get_repo_root()
DOCS_ROOT = os.path.join(REPO_ROOT, "docs")
BRAND_PATH = os.path.join(DOCS_ROOT, "assets", "brand", "vosslab-work-log-mark.svg")
MKDOCS_PATH = os.path.join(REPO_ROOT, "mkdocs.yml")
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
SVG_TAG = f"{{{SVG_NAMESPACE}}}svg"


#============================================
def _load_work_log_mark() -> ET.Element:
	"""
	Load the authored Vosslab Work Log mark.

	Returns:
		ET.Element: SVG root element.
	"""
	# The parser reads one fixed repository-owned asset; no external XML reaches this test.
	return ET.parse(BRAND_PATH).getroot()  # nosec B314


#============================================
def test_work_log_mark_has_scalable_svg_canvas() -> None:
	root = _load_work_log_mark()
	view_box = [float(value) for value in root.attrib["viewBox"].split()]
	assert root.tag == SVG_TAG
	assert len(view_box) == 4 and view_box[2] > 0 and view_box[3] > 0


#============================================
def test_work_log_mark_accessible_name_resolves() -> None:
	root = _load_work_log_mark()
	element_ids = {element.attrib["id"] for element in root.iter() if "id" in element.attrib}
	label_ids = root.attrib["aria-labelledby"].split()
	assert label_ids
	assert set(label_ids).issubset(element_ids)


#============================================
def test_work_log_mark_ids_are_unique() -> None:
	root = _load_work_log_mark()
	element_ids = [element.attrib["id"] for element in root.iter() if "id" in element.attrib]
	assert len(element_ids) == len(set(element_ids))


#============================================
def test_site_uses_one_owned_brand_asset() -> None:
	with open(MKDOCS_PATH, encoding="utf-8") as handle:
		config = yaml.safe_load(handle)
	logo_path = config["theme"]["logo"]
	assert logo_path == config["theme"]["favicon"]
	assert os.path.isfile(os.path.join(DOCS_ROOT, logo_path))
