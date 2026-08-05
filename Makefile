.PHONY: test demo serve verify

test:
	python -m unittest discover -s tests -v

demo:
	python scripts/run_demo.py

serve:
	python -m trinity_gate.http_api

verify: test demo

