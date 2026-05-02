# -----------------------------------------------------------------------------
#
# Extra project rules
#
# -----------------------------------------------------------------------------

.PHONY: release

release: clean ## Builds and uploads Python packages to PyPI
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*
	$(PYTHON) -m twine upload dist/*
