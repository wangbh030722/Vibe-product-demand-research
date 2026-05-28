PY := python3

.PHONY: all validate render index clean serve help research

help:
	@echo "Vibe Category Research · build"
	@echo "  make research IDEA=\"...\" SLUG=foo   full pipeline: scope→collect→cluster→render"
	@echo "  make validate     validate all data/*.json"
	@echo "  make render       render dist/<slug>.html for each data file"
	@echo "  make index        build dist/index.html"
	@echo "  make all          validate + render + index"
	@echo "  make serve        python -m http.server in repo root"
	@echo "  make clean        rm -rf dist/"

# One-command research:  make research IDEA="AI 智能体记忆" SLUG=agent-memory
research:
	@test -n "$(IDEA)" || (echo "ERROR: pass IDEA=\"...\"" && exit 1)
	@test -n "$(SLUG)" || (echo "ERROR: pass SLUG=..." && exit 1)
	$(PY) scripts/research.py --slug "$(SLUG)" --idea "$(IDEA)" $(if $(MARKET),--target-market "$(MARKET)",)

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
