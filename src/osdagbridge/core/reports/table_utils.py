# =============================================================================
# OsdagBridge report - table helpers
#
# 1. make_longtable()      build a new multi-page table that repeats its header
# 2. postprocess_tables()  retro-fit every table written as raw LaTeX in the
#                          chapter files:
#                            - repeat the header row on every page
#                            - keep \multirow groups (G1, G2 ... labels) together
#                          Styling values come from styles.py.
# Tables that cannot be parsed safely are left untouched and logged.
# =============================================================================
import logging
import re

from . import styles

logger = logging.getLogger(__name__)

_ROW_END = re.compile(r"\\\\(\*)?(\[[^\]]*\])?\s*$")
_LONGTABLE = re.compile(
    r"(\\begin\{longtable\}(?:\[[^\]]*\])?\{)(.*?)(\}[ \t]*\n)(.*?)(\\end\{longtable\})",
    re.S,
)
_MULTIROW_START = re.compile(r"\s*\\multirow\{(\d+)\}")


def _shade():
    return r"\rowcolor{tableHeader}" if styles.TABLE["header_shading"] else ""


def _count_columns(spec):
    """Number of columns in a tabular column spec such as |L{2cm}|p{3cm}|C{1cm}|."""
    stripped = re.sub(r"\{[^{}]*\}", "", spec)
    return len(re.findall(r"[LCRlcrpmbX]", stripped))


def _continued_row(ncols, spec):
    if not styles.TABLE["continued_label"]:
        return None
    return (r"\multicolumn{%d}{l}{\small\itshape Table \thetable{} (continued)}\\" % ncols)


def make_longtable(col_spec, headers, rows, caption=None):
    """Return LaTeX for a longtable whose header repeats on every page.

    headers : list of header cell strings (already LaTeX)
    rows    : list of lists of cell strings (already LaTeX-escaped)
    caption : table caption (LaTeX) or None
    """
    ncols = len(headers)
    head = _shade() + " & ".join(r"\textbf{%s}" % h for h in headers) + r" \\[6pt]"
    out = [r"\begin{longtable}{%s}" % col_spec]
    if caption:
        out.append(r"\caption{\textbf{%s}}\\" % caption)
    out += [r"\hline", head, r"\hline", r"\endfirsthead"]
    cont = _continued_row(ncols, col_spec) if caption else None
    if cont:
        out.append(cont)
    out += [r"\hline", head, r"\hline", r"\endhead"]
    for row in rows:
        out.append(" & ".join(row) + r" \\[6pt]")
        out.append(r"\hline")
    out.append(r"\end{longtable}")
    return "\n".join(out)


def _star(line):
    """Turn a row terminator '\\\\' into '\\\\*' (no page break after this row)."""
    return re.sub(r"\\\\(\[[^\]]*\])?\s*$", lambda m: r"\\*" + (m.group(1) or ""), line)


def _keep_multirow_groups(lines):
    out, remaining = [], 0
    for ln in lines:
        m = _MULTIROW_START.match(ln)
        if m:
            remaining = int(m.group(1))
            if remaining >= 3:
                # Top-align the group label. A vertically centred \multirow label is typeset
                # below its first row, so when longtable breaks the group across pages the
                # label (G1, G2 ... G4) lands in the footer. [t] keeps it on its first row.
                ln = ln.replace("\\multirow{", "\\multirow[t]{", 1)
        if remaining > 0 and _ROW_END.search(ln):
            if remaining > 1 and not _ROW_END.search(ln).group(1):
                ln = _star(ln)
            remaining -= 1
        out.append(ln)
    return out


def _empty_head_pair(lines, idx):
    """True if lines[idx:] is an empty '\\endfirsthead' + '\\endhead' pair. Returns lines to skip."""
    j = idx
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j < len(lines) and lines[j].strip() == r"\endfirsthead":
        k = j + 1
        while k < len(lines) and not lines[k].strip():
            k += 1
        if k < len(lines) and lines[k].strip() == r"\endhead":
            return k + 1
    return None


def _fallback(pre, spec, spec_end, lines, end):
    """Tables whose header cannot be detected: still end the caption with '\\\\' (a caption
    without it makes LaTeX report 'Misplaced \\noalign') and keep multirow groups together."""
    lines = list(lines)
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        if ln.lstrip().startswith(r"\caption"):
            cap = ln.rstrip()
            if cap.count("{") == cap.count("}") and not re.search(r"\\\\\*?\s*$", cap):
                lines[i] = cap + r"\\"
        break
    if styles.TABLE["keep_multirow_groups"]:
        lines = _keep_multirow_groups(lines)
    return pre + spec + spec_end + "\n".join(lines) + end


def _fix_longtable(m):
    pre, spec, spec_end, body, end = m.groups()
    whole = m.group(0)
    lines = body.split("\n")

    # already has a real repeating header -> only group handling
    has_head = re.search(r"\\endhead", body) is not None
    empty_pair = None
    if has_head:
        # an \endhead directly after \endfirsthead with nothing between is a no-op header
        for i in range(len(lines)):
            if lines[i].strip() == r"\endfirsthead":
                empty_pair = _empty_head_pair(lines, i)
                break
        if empty_pair is None:
            if styles.TABLE["keep_multirow_groups"]:
                lines = _keep_multirow_groups(lines)
            return pre + spec + spec_end + "\n".join(lines) + end

    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    caption = None
    if i < len(lines) and lines[i].lstrip().startswith(r"\caption"):
        cap = lines[i].rstrip()
        cap = re.sub(r"\\\\\*?\s*$", "", cap)
        if cap.count("{") != cap.count("}"):
            logger.warning("table header not fixed: multi-line caption")
            return _fallback(pre, spec, spec_end, lines, end)
        caption = cap
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or lines[i].strip() != r"\hline":
        logger.warning("table header not fixed (no \\hline before header): %s", (caption or spec)[:70])
        return _fallback(pre, spec, spec_end, lines, end)
    hs = i + 1
    k = hs
    while k < len(lines) and not _ROW_END.search(lines[k]):
        k += 1
    if k >= len(lines):
        return _fallback(pre, spec, spec_end, lines, end)
    header_lines = lines[hs:k + 1]
    if r"\textbf" not in "\n".join(header_lines):
        logger.warning("table header not fixed (header row not bold): %s", (caption or spec)[:70])
        return _fallback(pre, spec, spec_end, lines, end)
    nxt = k + 1
    if nxt >= len(lines) or lines[nxt].strip() != r"\hline":
        logger.warning("table header not fixed (no \\hline after header): %s", (caption or spec)[:70])
        return _fallback(pre, spec, spec_end, lines, end)
    rest = lines[nxt + 1:]
    if has_head:                      # drop the empty \endfirsthead/\endhead pair
        skip = _empty_head_pair(rest, 0)
        if skip is not None:
            rest = rest[skip:]
    if styles.TABLE["keep_multirow_groups"]:
        rest = _keep_multirow_groups(rest)

    shade = _shade()
    ncols = _count_columns(spec)
    new = []
    if caption:
        new.append(caption + r"\\")
    new += [r"\hline"]
    if shade:
        new.append(shade)
    new += header_lines + [r"\hline", r"\endfirsthead"]
    cont = _continued_row(ncols, spec) if caption else None
    if cont:
        new.append(cont)
    new.append(r"\hline")
    if shade:
        new.append(shade)
    new += header_lines + [r"\hline", r"\endhead"]
    return pre + spec + spec_end + "\n".join(new + rest) + end


def postprocess_tables(tex):
    """Apply repeating headers and multirow-group protection to every longtable in `tex`."""
    count = {"n": 0}

    def wrapper(m):
        count["n"] += 1
        return _fix_longtable(m)

    out = _LONGTABLE.sub(wrapper, tex)
    logger.info("postprocess_tables: %d longtables processed", count["n"])
    return out
