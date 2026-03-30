# Minimal Sphinx Makefile for the ExoArmur docs site

SPHINXBUILD   ?= sphinx-build
SOURCEDIR      = .
BUILDDIR       = _build
SPHINXOPTS     ?=
PAPEROPT_a4    = -D latex_paper_size=a4

.PHONY: help clean html

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

html:
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	@rm -rf "$(BUILDDIR)"
