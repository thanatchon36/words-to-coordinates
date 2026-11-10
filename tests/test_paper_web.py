"""The web reader's LaTeX preprocessing (code/paper_web.py) on the real paper source."""
from pathlib import Path

import pytest

import paper_web as pw

TEX = (Path(__file__).resolve().parents[1] / "paper" / "paper.tex").read_text(encoding="utf-8")


def test_labels_match_pdf_numbering():
    tex = TEX.replace("\\input{tab_e3.tex}", (pw.PAPER / "tab_e3.tex").read_text(encoding="utf-8"))
    labels = pw.number_labels(tex)
    assert labels["sec:intro"] == "1"
    assert labels["sec:precision"] == "3.3"
    assert labels["app:proof"] == "A" and labels["app:sim"] == "B"
    assert labels["fig:arch"] == "3"
    assert labels["tab:e3"] == "3" and labels["tab:protocol"] == "4"
    assert labels["alg:ds"] == "1" and labels["alg:mc"] == "2"
    assert labels["eq:pearson"] == "4"
    assert labels["prop:corr"] == "1"


def test_web_tex_has_no_unresolved_references_or_pdf_only_parts():
    tex, keywords = pw.web_tex(TEX)
    assert "\\ref{" not in tex and "\\eqref{" not in tex
    assert "\\begin{algorithmic}" not in tex and "\\begin{tikzpicture}" not in tex
    assert "figs/" not in tex and "figures/fig_architecture.png" in tex
    assert "Sustainable finance" in keywords


def test_algorithmic_nesting():
    body = "\\Require a\n\\Ensure b\n\\State x\n\\For{i}\n\\If{c}\n\\State y \\Comment{note}\n\\EndIf\n\\EndFor\n\\State \\Return z"
    out = pw.algorithmic_to_lists(body)
    assert out.count("\\begin{itemize}") == out.count("\\end{itemize}") == 3
    assert "\\textbf{return} z" in out and "\\emph{(note)}" in out


def test_unknown_reference_fails():
    with pytest.raises(RuntimeError):
        pw.resolve_refs("see \\ref{fig:missing}", {})
