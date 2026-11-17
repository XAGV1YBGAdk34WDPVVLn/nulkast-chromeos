.PHONY: catalog classify generate-script deploy-ssh test

BOARD ?= google_nocturne.10984.90.0
IP ?=

catalog:
	python3 scripts/chromeos_toolkit.py catalog

classify:
	python3 scripts/chromeos_toolkit.py classify --board "$(BOARD)"

generate-script:
	python3 scripts/chromeos_toolkit.py generate-script --lock-updates

deploy-ssh:
	python3 scripts/chromeos_toolkit.py deploy-ssh --host "$(IP)" --lock-updates

perf:
	python3 scripts/chromeos_toolkit.py perf --host "$(IP)"

test:
	python3 -m unittest discover -s tests -p "test_*.py" -v
