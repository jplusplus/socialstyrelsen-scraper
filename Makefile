
.PHONY: clean-pyc clean-build

install:
	pip install -r requirements.txt

clean-pyc:
	find . -name '*.pyc' -exec rm {} +
	find . -name '*.pyo' -exec rm {} +
	find . -name '*~' -exec rm {} +

tests: clean-pyc
	PYTHONPATH=. py.test tests --verbose

test: clean-pyc
	PYTHONPATH=. py.test $(file) --verbose
