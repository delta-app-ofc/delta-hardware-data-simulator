PYTHON ?= python
COLLECTION ?= consumption_summary
N ?= 10
DRY_RUN ?= --dry-run
OPTIONS ?=

.PHONY: dataload

dataload:
	$(PYTHON) -m dataload.cli $(COLLECTION) $(N) $(DRY_RUN) $(OPTIONS)
