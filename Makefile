PY ?= python3
E3_REPS := 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19

.PHONY: all data experiments figures table paper clean

all: figures table paper

data:
	bash get_data.sh

experiments:
	$(PY) code/run_parts.py e1 0,1,2,3,4,5,6
	$(PY) code/run_parts.py e2 0,1
	$(PY) code/run_parts.py e3 $(E3_REPS)
	$(PY) code/combine.py

figures:
	$(PY) code/fig_global_map.py
	$(PY) code/fig_thailand.py
	$(PY) code/fig_results.py

table:
	$(PY) code/make_table.py

paper:
	cd paper && pdflatex -interaction=nonstopmode paper && bibtex paper && pdflatex -interaction=nonstopmode paper && pdflatex -interaction=nonstopmode paper

clean:
	cd paper && rm -f *.aux *.log *.blg *.out *.synctex.gz
