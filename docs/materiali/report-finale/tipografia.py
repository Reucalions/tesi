"""Recognise report notation without changing the underlying evidence strings.

PDF, Word and Markdown share the same spans. Single-letter aliases are recognised
only in explicit linguistic contexts, OWL calls and designated semantic cells.
"""

from __future__ import annotations

import html
import re

ACCENT = "#006273"
BADGE = "#E7F1F3"

TERM = re.compile(
    r"\b(?!(?:GiB|arXiv)\b)(?:(?:[A-Z][a-z]+|[a-z]+)(?:[A-Z][a-zA-Z0-9]*)+|Tiny-ME|PROV-O|"
    r"OWL|ALN|ABox|TBox|DAG|KG|MCP|TP|FP|FN|F1|"
    r"Solutions|Bonus|[CG][1-5])\b"
    r"|\b(?:owl|rdfs|prov):[A-Za-z]+\b"
)
IDENTIFIER = re.compile(
    r"\b[A-Za-z][A-Za-z0-9-]*(?:_[A-Za-z0-9]+)+\b"
    r"|\b(?:CVE-\d{4}-\d{4,}|CWE-\d+)(?:_[A-Za-z0-9]+)*\b"
    r"|(?<!\w)--(?:backend-mode(?: (?:mockup|real))?|mode)\b"
    r"|https://[^\s]+?#"
    r"|\bch\.qos\.logback:logback-core\b"
)
ALIAS = re.compile(r"\b(?:[acprvP]|A_prep|A_val|A_sel|E_runtime)\b")
ALIAS_CONTEXTS = [
    re.compile(r"^(?P<alias>[acprv])(?=\s*:)"),
    re.compile(r"\b(?:asset|vulnerabilità|rimedio|individuo|accettare) (?P<alias>[acprv])\b"),
    re.compile(r"\b(?:profilo|descrizione|asserita) (?:di|per) (?P<alias>[acprv])\b"),
    re.compile(r"\b(?P<alias>a)(?= appartiene| è collegato| erediti)"),
    re.compile(r"\b(?P<alias>p)(?=, della CVE)"),
    re.compile(r"\b(?P<alias>r)(?= è anche)"),
]
OWL_CALL = re.compile(
    r"\b(?:ClassAssertion|ObjectPropertyAssertion|hasAffectedPackage|ABox|ALN|Tiny-ME)\([^()]*\)"
)


def runs(text, *, aliases=False):
    """Yield lossless (text, role) spans; roles are term, identifier or alias."""
    text = str(text)
    roles = [None] * len(text)

    def mark(start, end, role):
        roles[start:end] = [role] * (end - start)

    for pattern, role in [(TERM, "term"), (IDENTIFIER, "identifier")]:
        for match in pattern.finditer(text):
            mark(*match.span(), role)
    for match in re.finditer(r"\b(?:A_prep|A_val|A_sel|E_runtime)\b", text):
        mark(*match.span(), "alias")
    for pattern in ALIAS_CONTEXTS:
        for match in pattern.finditer(text):
            mark(*match.span("alias"), "alias")
    # Two coordinated graph nodes; the intervening Italian conjunction stays plain.
    for match in re.finditer(r"\bnodi, (?P<c>c) e (?P<r>r)\b", text):
        for name in ["c", "r"]:
            mark(*match.span(name), "alias")
    for call in OWL_CALL.finditer(text):
        for match in ALIAS.finditer(text, *call.span()):
            mark(*match.span(), "alias")
    if aliases:
        for match in ALIAS.finditer(text):
            mark(*match.span(), "alias")
    # Symbols of the illustrative mockup formula, never ordinary prose letters.
    if text.startswith("score(s)") or "dove B e I" in text:
        for match in re.finditer(r"\b(?:B|I|s|score|clamp)\b", text):
            mark(*match.span(), "alias")
    start = 0
    while start < len(text):
        end = start + 1
        while end < len(text) and roles[end] == roles[start]:
            end += 1
        yield text[start:end], roles[start]
        start = end


def semantic_alias_cell(block, column):
    return column == 0 and block.get("semantic_table_id") in {"aliases", "owl", "provenance"}


def pdf_markup(text, *, italic=False, aliases=False, header=False):
    out = []
    for value, role in runs(text, aliases=aliases):
        escaped = html.escape(value)
        if role is None or header:
            out.append(escaped)
            continue
        face = "ReportBoldItalic" if italic or role == "alias" else "ReportBold"
        background = f' backColor="{BADGE}"' if role == "identifier" else ""
        out.append(f'<font name="{face}" color="{ACCENT}"{background}>{escaped}</font>')
    return "".join(out)


def markdown(text, *, aliases=False):
    out = []
    for value, role in runs(text, aliases=aliases):
        if role == "identifier":
            out.append(f"`{value}`")
        elif role == "alias":
            out.append(f"***{value}***")
        elif role == "term":
            out.append(f"**{value}**")
        else:
            out.append(value)
    return "".join(out)
