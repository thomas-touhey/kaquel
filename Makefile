#!/usr/bin/make -f
include Makefile.msg

help:
	$(call amsg,Available targets are:)
	$(call amsg,)
	$(call amsg,- install)
	$(call amsg,- lint)
	$(call amsg,- build)
	$(call amsg,- test)
	$(call amsg,- clean)

install:
	$(call bmsg,Installing poetry and dependencies.)
	$(call qcmd,pip install -U poetry)
	$(call qcmd,poetry install)

lint:
	$(call bcmd,pre-commit,run,-poetry run pre-commit run --all-files)

build:
	$(call bcmd,poetry build,.,poetry build)

test:
	$(call qcmd,rm -rf htmlcov)
	$(call bcmd,pytest,--cov, \
		poetry run pytest $(O) $(SPECIFIC_TESTS))
	$(call bmsg,HTML coverage is available under the following directory:)
	$(call bmsg,file://$(realpath .)/htmlcov/index.html)

clean:
	$(call rmsg,Cleaning build and cache directories.)
	$(call qcmd,rm -rf build .coverage htmlcov .mypy_cache .pytest_cache)

.PHONY: help install lint build test clean
.PHONY: check-exports
