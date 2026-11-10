import os
import matplotlib as mpl

mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8.5,
    "axes.titlesize": 9,
    "axes.labelsize": 8.5,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "legend.frameon": False,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

# Okabe-Ito colour-blind-safe palette
OI = {"blue": "#0072B2", "orange": "#E69F00", "verm": "#D55E00", "green": "#009E73",
      "sky": "#56B4E9", "yellow": "#F0E442", "purple": "#CC79A7", "grey": "#8C8C8C",
      "black": "#000000"}
QCOL = {0: "#9E9E9E", 1: OI["orange"], 2: OI["verm"], 3: OI["blue"]}
FIGDIR = "paper/figs"
ASSETS = "assets"
os.makedirs(FIGDIR, exist_ok=True)
os.makedirs(ASSETS, exist_ok=True)
