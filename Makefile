PYTHON ?= python
COLLECTION ?= pulses_raw
N ?= 10
DRY_RUN ?=

.PHONY: dataload

dataload:
	$(PYTHON) -m dataload.cli $(COLLECTION) $(N) $(DRY_RUN)
