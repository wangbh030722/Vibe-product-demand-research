PY := python3

.PHONY: all validate render index clean serve help

help:
	@echo "Vibe Category Research · build"
	@echo "  make validate     validate all data/*.json"
	@echo "  make render       render dist/<slug>.html for each data file"
	@echo "  make index        build dist/index.html"
	@echo "  make all          validate + render + index"
	@echo "  make serve        python -m http.server in repo root"
	@echo "  make clean        rm -rf dist/"

validate:
	$(PY) scripts/validate_data.py --all

render:
	$(PY) scripts/render_report.py --all

index:
	$(PY) scripts/render_index.py

all: validate render index

clean:
	rm -rf dist/

serve:
	$(PY) -m http.server 8124
