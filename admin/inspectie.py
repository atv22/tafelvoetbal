"""Standalone Firestore inspectie script.

Plaats deze file in de `admin/` map zodat beheerders de database-structuur
kunnen inspecteren buiten de Streamlit UI.
"""
from __future__ import annotations
import pprint
import pandas as pd
import firestore_service as db


def run_inspection(max_docs: int = 250) -> dict:
    """Voert inspectie uit en retourneert het resultaat als dict.

    Geeft per collectie: sample_size, fields, examples (max 5).
    """
    expected = db.expected_schema()
    actual = db.inspect_collections(max_docs=max_docs)

    results = {}
    for coll in ["spelers", "uitslag", "elo", "requests"]:
        exp = expected.get(coll, {})
        act = actual.get(coll, {"fields": [], "sample_size": 0, "examples": []})

        exp_required = exp.get("required", set())
        exp_optional = exp.get("optional", set())
        exp_derived = exp.get("derived_only_in_app", set())
        act_fields = set(act.get("fields", []))

        missing = sorted(list((exp_required | exp_optional) - act_fields))
        unexpected = sorted(list(act_fields - (exp_required | exp_optional)))

        results[coll] = {
            "sample_size": act.get("sample_size", 0),
            "fields": sorted(list(act_fields)),
            "expected_required": sorted(list(exp_required)),
            "expected_optional": sorted(list(exp_optional)),
            "expected_derived_only_in_app": sorted(list(exp_derived)),
            "missing": missing,
            "unexpected": unexpected,
            "examples": act.get("examples", [])[:5],
        }

    return results


def print_inspection(results: dict) -> None:
    for coll, data in results.items():
        print("\n" + "#" * 60)
        print(f"Collectie: {coll}")
        print("-" * 60)
        print(f"Voorbeeld documenten (sample_size): {data.get('sample_size')}")
        print()
        print("Expected (required):")
        print("  ", ", ".join(data.get("expected_required") or ["—"]))
        print("Expected (optional):")
        print("  ", ", ".join(data.get("expected_optional") or ["—"]))
        print("Derived only in app:")
        print("  ", ", ".join(data.get("expected_derived_only_in_app") or ["—"]))
        print()
        print("Aangetroffen velden:")
        print("  ", ", ".join(data.get("fields") or ["—"]))
        print()
        print("Ontbrekend t.o.v. verwachting:")
        print("  ", ", ".join(data.get("missing") or ["—"]))
        print("Onverwacht (bestaat niet in app):")
        print("  ", ", ".join(data.get("unexpected") or ["—"]))
        print()
        if data.get("examples"):
            print("Voorbeelden (max 5):")
            try:
                df = pd.DataFrame(data.get("examples"))
                print(df.head(5).to_string(index=False))
            except Exception:
                pprint.pprint(data.get("examples"))


if __name__ == "__main__":
    print("Running Firestore inspection (admin/inspectie.py)")
    res = run_inspection(max_docs=250)
    print_inspection(res)
