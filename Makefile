.PHONY: setup test test-python test-server sim benchmark train frontend dev

setup:
	uv pip install -e ".[dev]"
	cd server && npm install
	npm install

test: test-python test-server

test-python:
	pytest -v

test-server:
	cd server && npm test

sim:
	python scripts/run_simulation.py --scenario typical_weekday --controller ucc_mpc

benchmark:
	python experiments/run_benchmark.py

train:
	python scripts/train_forecaster.py --epochs 6

dev-server:
	cd server && npm run dev

dev-frontend:
	npm run dev
