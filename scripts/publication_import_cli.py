"""Command-line parsing for the publication bundle importer."""

# Standard Library
import argparse


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse the one public bundle-import command."""
	parser = argparse.ArgumentParser(
		description="Place, render, and deploy one producer publication bundle."
	)
	bundle_input = parser.add_mutually_exclusive_group(required=True)
	bundle_input.add_argument(
		"-b",
		"--bundle",
		dest="bundle_path",
		help="Complete producer publication-bundle directory.",
	)
	bundle_input.add_argument(
		"--bundle-stdin",
		dest="bundle_stdin",
		action="store_true",
		help="Read one sealed producer publication bundle transfer from standard input.",
	)
	parser.add_argument(
		"--replace-existing",
		dest="replace_existing",
		action="store_true",
		help="Accepted for producer compatibility; same-date publication is always replaced.",
	)
	return parser.parse_args()
