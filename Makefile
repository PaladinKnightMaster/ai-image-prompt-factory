.PHONY: test validate regress baseline baseline-check gallery compile-golden

test:
	PYTHONPATH=src pytest -q

validate:
	PYTHONPATH=src python scripts/validate_repo.py

regress:
	PYTHONPATH=src python scripts/run_regression.py

baseline:
	PYTHONPATH=src python scripts/build_baselines.py

baseline-check:
	PYTHONPATH=src python -m aipf.cli baseline-check regression/baselines/golden_baselines.json

gallery:
	PYTHONPATH=src python website/generate_gallery.py

compile-golden: validate
	@echo "Golden prompts, evidence snapshots, and compatibility audits refreshed by validator."
