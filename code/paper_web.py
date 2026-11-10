"""Web reader for the preprint: paper/paper.tex -> docs/paper/index.html.

The LaTeX source is first simplified into something pandoc's LaTeX reader handles well (TikZ figure -> PNG,
PDF figures -> PNG previews, algorithmic -> nested step lists, cross-references resolved to the numbers
the PDF prints), then pandoc renders it with paper/reader.html. The headline numbers in the results strip
are read from results/results.json. GitHub Pages serves docs/ at
https://thanatchon36.github.io/words-to-coordinates/. Requires pandoc on PATH.

Usage (from the repository root): python code/paper_web.py
"""
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER, ASSETS, OUT = ROOT / "paper", ROOT / "assets", ROOT / "docs" / "paper"
REPO_URL = "https://github.com/thanatchon36/words-to-coordinates"
PAPER_URL = "https://thanatchon36.github.io/words-to-coordinates/paper/"
REFS_MARKER = "W2CREFERENCESMARKER"

THEOREMS = ("proposition", "corollary", "definition", "remark")
COUNTED = ("equation", "figure", "table", "algorithm") + THEOREMS
LINKED = ("sec", "app", "fig", "tab")  # label prefixes whose targets carry an id in the HTML


# --------------------------------------------------------------------------- LaTeX preprocessing

def braced(s: str, i: int) -> int:
    """Index just past the brace group that opens at s[i] == '{'."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return j + 1
    raise ValueError(f"unbalanced braces at {i}")


def arg(s: str, cmd: str) -> str:
    i = s.index(cmd + "{") + len(cmd)
    return s[i + 1:braced(s, i) - 1]


def number_labels(tex: str) -> dict:
    """Label -> the number LaTeX prints for it (sections, appendices, floats, equations, theorems)."""
    counters = {k: 0 for k in COUNTED}
    sec, sub, appendix, last = 0, 0, False, None
    event = re.compile(r"\\appendix\b|\\(sub)?section(\*?)\{|\\begin\{(%s)\}|\\label\{([^}]*)\}" % "|".join(COUNTED))
    labels = {}
    for m in event.finditer(tex):
        tok = m.group(0)
        if tok.startswith("\\appendix"):
            appendix, sec, sub = True, 0, 0
        elif m.group(4) is not None:
            if last is not None:
                labels[m.group(4)] = last
        elif m.group(3) is not None:
            counters[m.group(3)] += 1
            last = str(counters[m.group(3)])
        elif m.group(2):  # starred heading: not numbered
            last = None
        elif m.group(1):
            sub += 1
            last = f"{chr(64 + sec) if appendix else sec}.{sub}"
        else:
            sec, sub = sec + 1, 0
            last = chr(64 + sec) if appendix else str(sec)
    return labels


def resolve_refs(tex: str, labels: dict) -> str:
    def ref(m):
        cmd, key = m.group(1), m.group(2)
        if key not in labels:
            raise RuntimeError(f"unresolved reference {key}")
        num = f"({labels[key]})" if cmd == "eqref" else labels[key]
        return f"\\hyperref[{key}]{{{num}}}" if key.split(":")[0] in LINKED else num
    return re.sub(r"\\(ref|eqref)\{([^}]*)\}", ref, tex)


def number_equations(tex: str) -> str:
    """Print each equation's number next to it, as the PDF does (MathML has no automatic numbering)."""
    n = 0

    def tag(m):
        nonlocal n
        n += 1
        # texmath drops \\tag, so the number is typeset after the formula
        return f"\\begin{{equation}}{m.group(1)}\\qquad\\text{{({n})}}\n\\end{{equation}}"

    return re.sub(r"\\begin\{equation\}(.*?)\s*\\end\{equation\}", tag, tex, flags=re.DOTALL)


def appendix_letters(page: str) -> str:
    """pandoc numbers appendices on from the last section (10, 11); the PDF letters them (A, B)."""
    first = re.search(r'<h1 data-number="(\d+)" id="app:', page)
    if first is None:
        return page
    start = int(first.group(1))

    def letter(m):
        major, rest = int(m.group(2)), m.group(3) or ""
        return m.group(1) + (chr(65 + major - start) if major >= start else str(major)) + rest

    page = re.sub(r'(data-number=")(\d+)((?:\.\d+)*)', letter, page)
    return re.sub(r'((?:header|toc)-section-number">)(\d+)((?:\.\d+)*)', letter, page)


def algorithmic_to_lists(body: str) -> str:
    """algorithmic lines -> nested itemize, with for/if blocks indented."""
    out, opened = [], 0
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line == "\\small":
            continue
        line = re.sub(r"\\Comment\{(.*)\}\s*$", r" \\emph{(\1)}", line)
        if line.startswith("\\Require"):
            out.append("\\textbf{Input:} " + line[len("\\Require"):].strip() + "\n")
        elif line.startswith("\\Ensure"):
            out.append("\\textbf{Output:} " + line[len("\\Ensure"):].strip() + "\n")
            out.append("\\begin{itemize}")
            opened += 1
        elif line.startswith(("\\For{", "\\If{")):
            kw = "for" if line.startswith("\\For") else "if"
            cond_start = line.index("{")
            cond = line[cond_start + 1:braced(line, cond_start) - 1]
            tail = "do" if kw == "for" else "then"
            out.append(f"\\item \\textbf{{{kw}}} {cond} \\textbf{{{tail}}}")
            out.append("\\begin{itemize}")
            opened += 1
        elif line.startswith(("\\EndFor", "\\EndIf")):
            out.append("\\end{itemize}")
            opened -= 1
        elif line.startswith("\\State"):
            text = line[len("\\State"):].strip().replace("\\Return", "\\textbf{return}")
            out.append("\\item " + text)
        else:
            raise RuntimeError(f"unhandled algorithmic line: {line}")
    out += ["\\end{itemize}"] * opened
    return "\n".join(out)


def algorithms(tex: str, labels: dict) -> str:
    def repl(m):
        block = m.group(1)
        cap = arg(block, "\\caption")
        label = re.search(r"\\label\{([^}]*)\}", block).group(1)
        steps = re.search(r"\\begin\{algorithmic\}(?:\[\d+\])?(.*?)\\end\{algorithmic\}", block, re.DOTALL).group(1)
        return ("\\begin{quote}\n" + f"\\textbf{{Algorithm {labels[label]}.}} {cap}\n\n"
                + algorithmic_to_lists(steps) + "\n\\end{quote}")
    return re.sub(r"\\begin\{algorithm\}(?:\[[^\]]*\])?(.*?)\\end\{algorithm\}", repl, tex, flags=re.DOTALL)


def web_tex(tex: str) -> tuple[str, list[str]]:
    """paper.tex -> simplified LaTeX for pandoc, plus the keyword list."""
    tex = tex.replace("\\input{tab_e3.tex}", (PAPER / "tab_e3.tex").read_text(encoding="utf-8"))
    tex = tex.replace("\\input{fig_architecture.tex}", "\\includegraphics{figures/fig_architecture.png}")
    tex = re.sub(r"\\includegraphics(\[[^\]]*\])?\{figs/([\w-]+)\.pdf\}", r"\\includegraphics{figures/\2.png}", tex)
    # texmath needs a braced argument after \hat: \hat\x -> \hat{\mathbf{x}}
    tex = tex.replace("\\newcommand{\\x}{\\mathbf{x}}", "\\newcommand{\\x}{{\\mathbf{x}}}")
    tex = re.sub(r"\\bm\b", r"\\boldsymbol", tex)
    labels = number_labels(tex)
    tex = number_equations(tex)
    tex = algorithms(tex, labels)
    tex = resolve_refs(tex, labels)

    keywords = [k.strip() for k in arg(tex, "\\keywords").split("\\and")]
    preamble = "\n".join(
        line for line in tex[:tex.index("\\begin{document}")].splitlines()
        if line.startswith(("\\newcommand", "\\newtheorem", "\\theoremstyle", "\\title", "\\author", "\\date"))
    )
    body = tex[tex.index("\\begin{document}"):]
    body = re.sub(r"\\keywords\{.*?\}\n", "", body, count=1, flags=re.DOTALL)
    body = re.sub(r"\\bibliographystyle\{[^}]*\}\s*\\bibliography\{[^}]*\}", REFS_MARKER, body)
    # PDF-only layout commands
    body = re.sub(r"\\(fontsize\{[^}]*\}\{[^}]*\}\\selectfont|setlength\{[^}]*\}\{[^}]*\}|small|centering|maketitle)\b", "", body)
    return "\\documentclass{article}\n\\usepackage{amsthm}\n" + preamble + "\n" + body, keywords


# --------------------------------------------------------------------------- HTML post-processing

def number_captions(page: str) -> str:
    count = {"caption": 0, "figcaption": 0}

    def caption(m):
        tag, attrs, para = m.group(1), m.group(2), m.group(3) or ""
        count[tag] += 1
        word = "Table" if tag == "caption" else "Figure"
        return f"<{tag}{attrs}>{para}<b>{word} {count[tag]}.</b> "

    return re.sub(r"<(caption|figcaption)(\b[^>]*)>(\s*<p>)?", caption, page)


def results_strip() -> str:
    r = json.loads((ROOT / "results" / "results.json").read_text())
    e1, e2, s = r["E1"], r["E2"], r["E3"]["summary"]
    ells, var = e1["ells"], e2["variants"]
    country_local = max(row[-1] for ell, row in zip(ells, e1["firm_mean"]) if ell <= 100)
    country_global = e1["firm_mean"][ells.index(1000)][-1]
    acc = e2["acc_mean"][e2["ells"].index(25)]
    eps20 = e2["eps"].index(0.2)
    items = [
        ("Theory", "pos", f"Corr = ℓ²/(ℓ²+σ²) matches simulation: mean absolute deviation {e1['mad']:.3f}",
         f"{len(ells) * len(e1['sigmas'])} combinations of correlation length ℓ and location error σ"),
        ("Design rule", "pos", "σ ≤ ℓ/3 keeps the exposure correlation at 0.9",
         "turns an accuracy target into a geocoding specification per hazard"),
        ("Country geocoding", "ref", f"Firm-level rank correlation ≤ {country_local:.2f} for ℓ ≤ 100 km",
         f"at most {country_global:.2f} even for ℓ = 1,000 km"),
        ("Location error", "ref", f"Quadrant accuracy 1.00 → {acc[var.index('25 km')][0]:.2f}",
         "local hazard (ℓ = 25 km) with city-level error (σ = 25 km)"),
        ("Extraction error", "ref", f"Quadrant accuracy 1.00 → {acc[var.index('exact')][eps20]:.3f}",
         "local hazard (ℓ = 25 km), 20% extraction error rate"),
        ("Calibration", "pos", f"ECE {s['p_extr']['ece'][0]:.3f} → {s['p_full']['ece'][0]:.3f} with full propagation",
         "extraction-only uncertainty vs. extraction + location + hazard model"),
        ("Silent risk", "pos", f"Precision {s['p_full']['prec80'][0]:.2f} when flagging only at P(silent) ≥ 0.8",
         f"vs. {s['point']['prec'][0]:.2f} for a point estimate"),
        ("Real firms", "null", "Disclosure gaps for real companies: pending",
         "hazards, disclosures and extraction errors are synthetic; only asset locations are real"),
    ]
    return "\n".join(
        f'<li class="r r-{style}"><span class="r-id">{html.escape(label)}</span>'
        f'<span class="r-text">{html.escape(finding)}<small>{html.escape(detail)}</small></span></li>'
        for label, style, finding, detail in items
    )


def build() -> Path:
    if shutil.which("pandoc") is None:
        raise RuntimeError("pandoc not found; install pandoc to build the web reader")
    tex, keywords = web_tex((PAPER / "paper.tex").read_text(encoding="utf-8"))
    cmd = [
        "pandoc", "--from=latex", "--to=html5", "--mathml", "--wrap=none", "--standalone",
        "--template=reader.html", "--number-sections", "--toc", "--toc-depth=1",
        "--citeproc", "--bibliography=references.bib", "--metadata=link-citations:true",
        "--metadata=pagetitle:Words to Coordinates",
        "--metadata=description:Preprint: an uncertainty-aware NLP-geospatial framework for measuring the gap "
        "between disclosed and physical climate risk.",
    ] + [f"--metadata=keywords:{k}" for k in keywords]
    page = subprocess.run(cmd, input=tex, capture_output=True, text=True, check=True,
                          cwd=str(PAPER), timeout=300).stdout

    page = number_captions(page)
    page = appendix_letters(page)
    page = re.sub(r"<img\b", '<img loading="lazy"', page)
    page = re.sub(r'(<img[^>]*?)\s(?:style|width|height)="[^"]*"', r"\1", page)
    page = re.sub(r"<table\b[^>]*>\s*<caption>(.*?)</caption>(.*?)</table>",
                  r'<div class="tbl"><p class="tcap">\1</p><div class="tscroll"><table>\2</table></div></div>',
                  page, flags=re.DOTALL)
    page = re.sub(r"<colgroup>.*?</colgroup>\s*", "", page, flags=re.DOTALL)
    page = re.sub(r"<blockquote>\s*(<p><strong>Algorithm \d+\.</strong>.*?)</blockquote>",
                  r'<div class="algo">\1</div>', page, flags=re.DOTALL)
    # citeproc appends the reference list at the end; move it to where \bibliography stood
    refs = re.search(r'<div id="refs".*?\n</div>\n(?=\s*</article>)', page, re.DOTALL)
    if refs is None or f"<p>{REFS_MARKER}</p>" not in page:
        raise RuntimeError("reference list or its marker not found")
    page = page.replace(refs.group(0), "")
    page = page.replace(f"<p>{REFS_MARKER}</p>", '<h1 class="unnumbered" id="references">References</h1>\n' + refs.group(0))

    title = html.unescape(re.sub(r"<[^>]+>", "", re.search(r"<h1>(.*?)</h1>", page, re.DOTALL).group(1)))
    bib = ("@misc{chongmankhong2026words,\n"
           "  author = {Chongmankhong, Thanatchon},\n"
           f"  title  = {{{title}}},\n"
           "  year   = {2026},\n"
           "  note   = {Preprint},\n"
           f"  url    = {{{PAPER_URL}}}\n"
           "}")
    fill = {
        "<!--ACTIONS-->": ('<li><a href="paper.pdf">Download PDF</a></li>'
                           f'<li><a href="{REPO_URL}">Code and replication</a></li>'
                           f'<li><a href="{REPO_URL}/releases">Releases</a></li>'),
        "<!--RESULTS-NOTE-->": ("Headline numbers from the simulation study, read from results/results.json. Asset "
                                "locations are real (Global Power Plant Database v1.3.0); hazard fields, disclosures and "
                                "extraction errors are synthetic. Green: theory confirmed; amber: measured sensitivity; "
                                "grey: pending."),
        "<!--RESULTS-->": results_strip(),
        "<!--CITE-->": f"<h2>How to cite</h2><pre><code>{html.escape(bib)}</code></pre>",
        "<!--COLOPHON-->": ("<p>Rendered from <code>paper/paper.tex</code> by <code>code/paper_web.py</code> "
                            "(<code>make web</code>) with pandoc. Equations are MathML; figures are the PNG previews "
                            "in <code>assets/</code>. The PDF is authoritative.</p>"),
    }
    for marker, value in fill.items():
        if marker not in page:
            raise RuntimeError(f"reader.html lacks {marker}")
        page = page.replace(marker, value)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    shutil.copyfile(PAPER / "paper.pdf", OUT / "paper.pdf")
    (OUT / "figures").mkdir(exist_ok=True)
    for name in sorted(set(re.findall(r'src="figures/([\w.-]+)"', page))):
        shutil.copyfile(ASSETS / name, OUT / "figures" / name)
    return OUT / "index.html"


if __name__ == "__main__":
    print(build(), file=sys.stderr)
