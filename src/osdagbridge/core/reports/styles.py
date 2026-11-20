# =============================================================================
# OsdagBridge report - central style definitions
#
# Single source of truth for the look of the generated LaTeX design report:
# page geometry, colours, table layout, header/footer and chart appearance.
# Report chapters and the preamble must read their values from here instead
# of hard-coding them.
# =============================================================================

# --- Colours (HTML hex, no leading '#') -------------------------------------
COLORS = {
    "osdagGreen": "91B014",    # brand colour: rules, header/footer text
    "tableHeader": "E9F0CC",   # light tint of osdagGreen for table header rows
    "statusPass": "2E7D32",    # PASS / UR <= 1.0
    "statusFail": "C62828",    # FAIL / UR > 1.0
}

# --- Page geometry ------------------------------------------------------------
PAGE = {
    "documentclass_options": "12pt,a4paper",
    "geometry": "a4paper, margin=1in",
    "line_stretch": "1.15",
}

# --- Tables ---------------------------------------------------------------------
TABLE = {
    "tabcolsep": "6pt",
    "arraystretch": "1.12",
    "LTpre": "0pt",
    "LTpost": "6pt",
    "arrayrulewidth": "0.5pt",
    "extrarowheight": "0.6pt",
    # floating tables: break to a new page first when less than this much room is left
    "needspace": r"5\baselineskip",
    # longtable breaks pages by itself. A \needspace hook in front of it made longtable print a
    # stray "(continued)" header at the top of the page, so it is off (None) for longtables.
    "needspace_longtable": None,
    "header_shading": True,         # shade table header rows with COLORS["tableHeader"]
    "continued_label": True,        # "Table x.y (continued)" on follow-on pages
    "keep_multirow_groups": True,   # never split a \multirow group (G1/G2/... label) over a page break
}

# --- Charts (matplotlib) --------------------------------------------------------
CHART = {
    "dpi": 200,
    "figsize": (7.0, 3.4),         # inches; fits the 6.3in text width
    "font_size": 9,
    "bar_pass": "#" + COLORS["osdagGreen"],
    "bar_fail": "#" + COLORS["statusFail"],
    "bar_neutral": "#4C6A8A",
    "threshold_color": "#" + COLORS["statusFail"],
    "grid_alpha": 0.3,
}


def geometry_line():
    return r"\usepackage[" + PAGE["geometry"] + r"]{geometry}"


def color_definitions():
    return "\n".join(
        r"\definecolor{%s}{HTML}{%s}" % (name, hexval) for name, hexval in COLORS.items()
    )


def table_layout():
    t = TABLE
    return "\n".join([
        r"% Table layout and spacing: consistent padding, row height, and longtable pre/post skips",
        r"\setlength{\tabcolsep}{%s}" % t["tabcolsep"],
        r"\renewcommand{\arraystretch}{%s}" % t["arraystretch"],
        r"\setlength{\LTpre}{%s}" % t["LTpre"],
        r"\setlength{\LTpost}{%s}" % t["LTpost"],
        r"% Table rules (outline thickness) and small extra row height for clarity",
        r"\setlength{\arrayrulewidth}{%s}" % t["arrayrulewidth"],
        r"\setlength{\extrarowheight}{%s}" % t["extrarowheight"],
        "",
        r"% Floating tables: if too little room remains, break to the next page first.",
        r"\BeforeBeginEnvironment{table}{\needspace{%s}}" % t["needspace"],
    ] + ([r"\BeforeBeginEnvironment{longtable}{\needspace{%s}}" % t["needspace_longtable"]]
         if t["needspace_longtable"] else []))


_PAGE_STYLES = r"""
\fancypagestyle{main}{
  \fancyhf{}
  \fancyhead[L]{@@PN@@ $|$ @@JN@@}
  \fancyhead[R]{@@RD@@ $|$ @@RV@@}
  \fancyfoot[L]{Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}
  \fancyfoot[R]{Page \thepage\ of \pageref{LastPage}}
  \renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{2pt}}
  \renewcommand{\footrule}{%
    \ifbool{hasSDonPage}{%
      \vspace{-20pt}%
      \hbox to \headwidth{\textcolor{black}{\footnotesize\textit{* Software default value}}\hfil}%
      \vspace{4pt}%
    }{%
      \vspace{-8pt}%
    }%
    \color{osdagGreen}\hrule width\headwidth height 1pt \vspace{6pt}%
  }
}
\fancypagestyle{plain}{
  \fancyhf{}
  \fancyhead[L]{@@PN@@ $|$ @@JN@@}
  \fancyhead[R]{@@RD@@ $|$ @@RV@@}
  \fancyfoot[L]{Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}
  \fancyfoot[R]{Page \thepage\ of \pageref{LastPage}}
  \renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{2pt}}
  \renewcommand{\footrule}{%
    \ifbool{hasSDonPage}{%
      \vspace{-20pt}%
      \hbox to \headwidth{\textcolor{black}{\footnotesize\textit{* Software default value}}\hfil}%
      \vspace{4pt}%
    }{%
      \vspace{-8pt}%
    }%
    \color{osdagGreen}\hrule width\headwidth height 1pt \vspace{6pt}%
  }
}
\fancypagestyle{firstpage}{
  \fancyhf{}
  \renewcommand{\headrulewidth}{0pt}
  \fancyfoot[L]{Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}
  \fancyfoot[R]{Page \thepage\ of \pageref{LastPage}}
  \renewcommand{\footrule}{\vspace{-8pt}\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{6pt}}
}
"""


def page_styles(project_name, job_number, report_date, report_version):
    """Header/footer page styles (main, plain, firstpage). Arguments must already be LaTeX-escaped."""
    return (_PAGE_STYLES.strip("\n")
            .replace("@@PN@@", project_name)
            .replace("@@JN@@", job_number)
            .replace("@@RD@@", report_date)
            .replace("@@RV@@", report_version))
