"""Rigenera il catalogo, il BibTeX e la bibliografia della relazione da fonti.json."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    records = json.loads((HERE / "fonti.json").read_text())
    bibliography = [
        "## Bibliografia e fonti consultate",
        "",
        "Riferimenti verificati nella revisione del 17 settembre 2026. Le fonti teoriche",
        "aggiunte in questa fase non sono attribuite retroattivamente allo sviluppo.",
        "Ambito e parti consultate sono registrati in `docs/riferimenti/fonti.json`.",
        "Le fonti grafiche sono [POLIBA] e [PT-SANS]; il logo proviene dal sito",
        "dell'Ateneo, con URL e hash in `docs/materiali/assets/sources.json`.",
        "",
    ]
    catalog = [
        "# Registro delle fonti",
        "",
        "Per la derivazione della formula e le attribuzioni, "
        "leggi [fonti e scelte](../fonti-e-scelte.md).",
        "I riferimenti sono identificati con gli stessi codici usati nella relazione.",
        "",
        "`fonti.json` è il registro principale. Dopo una modifica, esegui dalla radice:",
        "",
        "```bash",
        "python3 docs/riferimenti/aggiorna_fonti.py",
        "/tmp/tesi-materiali-venv/bin/python docs/materiali/genera_materiali.py",
        "```",
        "",
        "Il primo comando aggiorna questo catalogo, il BibTeX e la bibliografia Markdown;",
        "il secondo rigenera i materiali. Non vengono effettuate inferenze o chiamate di rete.",
        "",
    ]
    bib = []
    for r in records:
        label = f"[{r['id']}]"
        year = r["year"] or "s.d."
        citation = f"**{label}** {r['author']}. *{r['title']}*. {year}."
        target = r["url"] or ("riferimenti/" + r["local_file"])
        bibliography.extend([citation, "", f"Fonte: [{target}]({target}).", ""])
        catalog.extend(
            [
                f"## {label} {r['title']}",
                "",
                citation,
                "",
                f"Fonte: {r['url'] or r['local_file']}",
                "",
                "**Ambito:** " + r["scope"],
                "",
                "**Consultazione:** " + r["consulted"] + "; " + r["consultation_status"] + ".",
                "",
            ]
        )
        if r.get("sha256"):
            catalog.extend(["SHA-256 della copia: `" + r["sha256"] + "`.", ""])
        author = (
            r["author"] if " and " in r["author"] or r["id"] == "TESI" else "{" + r["author"] + "}"
        )
        fields = {
            "author": author,
            "title": "{" + r["title"] + "}",
            "note": r["scope"] + " Consultato il " + r["consulted"] + ".",
        }
        if r["year"]:
            fields["year"] = r["year"]
        if r["url"]:
            fields["url"] = r["url"]
        if r["local_file"]:
            fields["howpublished"] = "Documento progettuale non pubblicato: " + r["local_file"]
        entries = [
            "  " + key + " = {" + value.replace("%", r"\%").replace("&", r"\&") + "}"
            for key, value in fields.items()
        ]
        bib.append("@misc{" + r["id"] + ",\n" + ",\n".join(entries) + "\n}\n")
    (HERE / "README.md").write_text("\n".join(catalog))
    (HERE / "bibliografia.bib").write_text("\n".join(bib))
    report = HERE.parent / "relazione-mockup.md"
    body = report.read_text().split("\n## Bibliografia e fonti consultate", 1)[0].rstrip()
    report.write_text(body + "\n\n" + "\n".join(bibliography))


if __name__ == "__main__":
    main()
