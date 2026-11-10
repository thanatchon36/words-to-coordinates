"""Writes paper/tab_e3.tex (Table 3 of the paper) from results/results.json."""
import json

R = json.load(open("results/results.json"))["E3"]["summary"]


def f(m, k, bold=False):
    mu, sd = R[m][k]
    s = f"{mu:.3f}"
    s = f"\\textbf{{{s}}}" if bold else s
    return f"{s} ({sd:.3f})".replace("(0.", "(.")


rows = [f"Point estimate & {f('point', 'brier')} & -- & -- & {f('point', 'prec')} & "
        f"{f('point', 'rec')} & {100 * R['point']['flag'][0]:.1f}\\% \\\\"]
names = {"p_extr": "MC: extraction only", "p_loc": "MC: location + hazard model",
         "p_full": "MC: full propagation"}
for k, nm in names.items():
    b = k == "p_full"
    rows.append(f"{nm} & {f(k, 'brier', b)} & {f(k, 'ece', b)} & {f(k, 'ap', b)} & "
                f"{f(k, 'prec80', b)} & {f(k, 'rec80')} & {100 * R[k]['flag80'][0]:.1f}\\% \\\\")

tex = r"""\begin{table}[t]
\caption{Uncertainty propagation for identifying silent-risk firms (E3): means over 20 replications, standard deviations in parentheses. Brier scores and expected calibration error (ECE) evaluate $P(Q_i=\text{silent})$; AP is average precision. Precision, recall and the share of firms flagged refer to the point classification for the point estimate and to the rule $P(Q_i=\text{silent}) \geq 0.8$ for the Monte Carlo (MC) variants. Bold marks the best value in each probabilistic or precision column.}
\label{tab:e3}
\centering
\fontsize{8}{10}\selectfont
\setlength{\tabcolsep}{4.5pt}
\begin{tabular}{@{}lcccccc@{}}
\toprule
& \multicolumn{3}{c}{Probabilistic quality} & \multicolumn{3}{c}{Flagging silent-risk firms} \\
\cmidrule(lr){2-4}\cmidrule(l){5-7}
Method & Brier $\downarrow$ & ECE $\downarrow$ & AP $\uparrow$ & Precision $\uparrow$ & Recall & Flagged \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
open("paper/tab_e3.tex", "w").write(tex)
print("wrote paper/tab_e3.tex")
