PY ?= .venv/bin/python
E3_REPS := 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19

.PHONY: setup data experiments figures banner table paper web test all clean

setup:          ## create venv and install dependencies (needs uv)
	uv venv .venv --python 3.12
	uv pip install --python .venv/bin/python -r pyproject.toml --extra dev

data:           ## download GPPD v1.3.0 and Natural Earth boundaries into data/
	bash get_data.sh

experiments:    ## rerun E1-E3 (about 6 minutes) and merge into results/results.json
	$(PY) code/run_parts.py e1 0,1,2,3,4,5,6
	$(PY) code/run_parts.py e2 0,1
	$(PY) code/run_parts.py e3 $(E3_REPS)
	$(PY) code/combine.py

figures:        ## paper/figs/*.pdf and assets/*.png (needs data/)
	$(PY) code/fig_global_map.py
	$(PY) code/fig_thailand.py
	$(PY) code/fig_results.py

banner:         ## README banner -> docs/assets/banner.png (needs data/)
	$(PY) code/make_banner.py

table:          ## paper/tab_e3.tex from results/results.json
	$(PY) code/make_table.py

paper:          ## compile paper/paper.pdf (needs a LaTeX distribution)
	cd paper && pdflatex -interaction=nonstopmode paper && bibtex paper && pdflatex -interaction=nonstopmode paper && pdflatex -interaction=nonstopmode paper

web:            ## web reader -> docs/paper/index.html (needs pandoc), served on GitHub Pages
	$(PY) code/paper_web.py

test:           ## unit tests (no downloaded data needed)
	$(PY) -m pytest -q

all: figures table paper web

clean:
	cd paper && rm -f *.aux *.log *.blg *.out *.synctex.gz
