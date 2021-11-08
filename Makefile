install:
	pip3 install -r requirements.txt

tests:
	PYTHONPATH=. py.test tests --verbose

test:
	PYTHONPATH=. py.test $(file) --verbose
