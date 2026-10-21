"""
Build the OSCAL System Security Plan and POA&M from the YAML sources, validate
them, and render human-readable Markdown.

  python tools/build.py            # build + validate, write oscal/*.json and docs/*.md
  python tools/build.py --check    # validate only; fail if generated files are stale (CI)

Checks performed:
  1. Every control ID exists in the NIST SP 800-53 Rev 5 MODERATE baseline.
  2. Every component referenced by a control statement is defined.
  3. Every partial/planned control has a POA&M item, and every POA&M item points
     at a control that is actually partial/planned in the SSP.
  4. Both documents validate against the official NIST OSCAL 1.1.2 JSON schemas.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "source"
OUT_SSP = ROOT / "oscal" / "ssp.json"
OUT_POAM = ROOT / "oscal" / "poam.json"
OUT_SSP_MD = ROOT / "docs" / "SSP.md"
OUT_POAM_MD = ROOT / "docs" / "POAM.md"
OSCAL_VERSION = "1.1.2"
NS = uuid.UUID("6f1c4a2e-0b7d-4e55-9a3c-5d8f0e2b7c11")   # namespace for deterministic UUIDs
PROFILE_HREF = ("https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/"
                "json/NIST_SP-800-53_rev5_MODERATE-baseline_profile.json")
FIPS = {"low": "fips-199-low", "moderate": "fips-199-moderate", "high": "fips-199-high"}
OPEN_STATES = {"partial", "planned"}


def uid(*parts: str) -> str:
    return str(uuid.uuid5(NS, "/".join(parts)))


def oscal_control_id(cid: str) -> str:
    """'AC-2(3)' -> 'ac-2.3'"""
    m = re.fullmatch(r"([A-Z]{2})-(\d+)(?:\((\d+)\))?", cid.strip())
    if not m:
        raise ValueError(f"bad control id {cid!r}")
    return f"{m[1].lower()}-{m[2]}" + (f".{m[3]}" if m[3] else "")


def load():
    sysd = yaml.safe_load((SRC / "system.yaml").read_text())
    controls = yaml.safe_load((SRC / "controls.yaml").read_text())
    poam = yaml.safe_load((SRC / "poam.yaml").read_text())
    baseline = json.loads((ROOT / "baseline" / "moderate-baseline.json").read_text())["controls"]
    return sysd, controls, poam, baseline


# --------------------------------------------------------------------------- checks
def cross_check(sysd, controls, poam, baseline) -> list[str]:
    errs = []
    comp_ids = {c["id"] for c in sysd["components"]}
    open_controls = set()
    for cid, stmts in controls.items():
        try:
            oid = oscal_control_id(cid)
        except ValueError as e:
            errs.append(str(e)); continue
        if oid not in baseline:
            errs.append(f"{cid}: not in the NIST 800-53 Rev 5 MODERATE baseline")
        for s in stmts:
            if s["component"] not in comp_ids:
                errs.append(f"{cid}: unknown component '{s['component']}'")
            if s["status"] not in {"implemented", "partial", "planned", "alternative", "not-applicable"}:
                errs.append(f"{cid}: bad status '{s['status']}'")
            if s["status"] in OPEN_STATES:
                open_controls.add(cid)
    poam_controls = {c for it in poam["items"] for c in it["controls"]}
    for cid in sorted(open_controls - poam_controls):
        errs.append(f"{cid}: partial/planned in the SSP but has no POA&M item")
    for it in poam["items"]:
        for c in it["controls"]:
            if c not in open_controls:
                errs.append(f"{it['id']}: references {c}, which is not partial/planned in the SSP")
        if it["risk"] not in {"low", "moderate", "high"}:
            errs.append(f"{it['id']}: bad risk '{it['risk']}'")
        if it["milestones"] and max(m["date"] for m in it["milestones"]) != it["scheduled_completion"]:
            errs.append(f"{it['id']}: last milestone date must equal scheduled_completion")
    return errs


# --------------------------------------------------------------------------- builders
def build_ssp(sysd, controls, baseline) -> dict:
    s = sysd["system"]
    ts = f"{s['published']}T00:00:00Z"
    comp_uuid = {c["id"]: uid("component", c["id"]) for c in sysd["components"]}
    party_uuid = {p["id"]: uid("party", p["id"]) for p in sysd["parties"]}
    worst = lambda k: max((t[k] for t in sysd["information_types"]), key=["low", "moderate", "high"].index)

    reqs = []
    for cid, stmts in controls.items():
        oid = oscal_control_id(cid)
        reqs.append({
            "uuid": uid("req", oid),
            "control-id": oid,
            "by-components": [{
                "component-uuid": comp_uuid[x["component"]],
                "uuid": uid("byc", oid, x["component"], str(i)),
                "description": " ".join(x["statement"].split()),
                "implementation-status": {"state": x["status"]},
            } for i, x in enumerate(stmts)],
        })

    return {"system-security-plan": {
        "uuid": uid("ssp", s["id"]),
        "metadata": {
            "title": f"{s['name']} System Security Plan",
            "last-modified": ts,
            "version": s["version"],
            "oscal-version": OSCAL_VERSION,
            "roles": [{"id": r["id"], "title": r["title"]} for r in sysd["roles"]],
            "parties": [{"uuid": party_uuid[p["id"]], "type": p["type"], "name": p["name"]} for p in sysd["parties"]],
            "responsible-parties": [{"role-id": r, "party-uuids": [party_uuid[p]]}
                                    for r, p in sysd["responsible_parties"].items()],
            "remarks": "Fictional system created for a portfolio demonstration. Not an actual federal system.",
        },
        "import-profile": {"href": PROFILE_HREF},
        "system-characteristics": {
            "system-ids": [{"identifier-type": "https://ietf.org/rfc/rfc4122", "id": uid("system", s["id"])}],
            "system-name": s["name"],
            "system-name-short": s["short_name"],
            "description": " ".join(s["description"].split()),
            "security-sensitivity-level": FIPS[s["sensitivity"]],
            "system-information": {"information-types": [{
                "uuid": uid("infotype", t["title"]),
                "title": t["title"],
                "description": t["description"],
                "confidentiality-impact": {"base": FIPS[t["c"]]},
                "integrity-impact": {"base": FIPS[t["i"]]},
                "availability-impact": {"base": FIPS[t["a"]]},
            } for t in sysd["information_types"]]},
            "security-impact-level": {
                "security-objective-confidentiality": FIPS[worst("c")],
                "security-objective-integrity": FIPS[worst("i")],
                "security-objective-availability": FIPS[worst("a")],
            },
            "status": {"state": s["status"]},
            "authorization-boundary": {"description": " ".join(s["boundary"].split())},
            "network-architecture": {"description": " ".join(s["network"].split())},
            "data-flow": {"description": " ".join(s["data_flow"].split())},
        },
        "system-implementation": {
            "users": [{
                "uuid": uid("user", u["title"]),
                "title": u["title"],
                "role-ids": [u["role"]],
                "authorized-privileges": [{"title": p, "functions-performed": [p]} for p in u["privileges"]],
            } for u in sysd["users"]],
            "components": [{
                "uuid": comp_uuid[c["id"]],
                "type": c["type"],
                "title": c["title"],
                "description": c["description"],
                "status": {"state": "operational"},
            } for c in sysd["components"]],
        },
        "control-implementation": {
            "description": ("Implementation of a representative subset of the NIST SP 800-53 Rev 5 MODERATE "
                            "baseline. Partial and planned items are tracked in the POA&M."),
            "implemented-requirements": reqs,
        },
    }}


def build_poam(sysd, poam) -> dict:
    s = sysd["system"]
    ts = f"{s['published']}T00:00:00Z"
    risks, items, observations = [], [], []
    for it in poam["items"]:
        obs_id, risk_id = uid("obs", it["id"]), uid("risk", it["id"])
        observations.append({
            "uuid": obs_id,
            "title": it["title"],
            "description": it["weakness"],
            "methods": ["EXAMINE"],
            "types": ["finding"],
            "collected": f"{it['detected']}T00:00:00Z",
            "remarks": f"Source: {it['source']}",
        })
        risks.append({
            "uuid": risk_id,
            "title": it["title"],
            "description": it["weakness"],
            "statement": f"Affects {', '.join(it['controls'])}. Risk rated {it['risk']}.",
            "props": [{"name": "risk-level", "value": it["risk"]}],
            "status": "open",
            "deadline": f"{it['scheduled_completion']}T00:00:00Z",
            "remediations": [{
                "uuid": uid("rem", it["id"]),
                "lifecycle": "planned",
                "title": "Planned remediation",
                "description": it["remediation"],
                "tasks": [{
                    "uuid": uid("task", it["id"], m["date"]),
                    "type": "milestone",
                    "title": m["text"],
                    "timing": {"on-date": {"date": f"{m['date']}T00:00:00Z"}},
                } for m in it["milestones"]],
            }],
            "related-observations": [{"observation-uuid": obs_id}],
        })
        items.append({
            "uuid": uid("poam-item", it["id"]),
            "title": it["title"],
            "description": it["weakness"],
            "props": [{"name": "POAM-ID", "ns": "https://fedramp.gov/ns/oscal", "value": it["id"]}],
            "related-observations": [{"observation-uuid": obs_id}],
            "related-risks": [{"risk-uuid": risk_id}],
            "remarks": f"Controls: {', '.join(it['controls'])}. Owner role: {it['owner']}.",
        })
    return {"plan-of-action-and-milestones": {
        "uuid": uid("poam", s["id"]),
        "metadata": {
            "title": f"{s['name']} Plan of Action and Milestones",
            "last-modified": ts,
            "version": s["version"],
            "oscal-version": OSCAL_VERSION,
            "remarks": "Fictional system created for a portfolio demonstration.",
        },
        "import-ssp": {"href": "ssp.json"},
        "system-id": {"identifier-type": "https://ietf.org/rfc/rfc4122", "id": uid("system", s["id"])},
        "observations": observations,
        "risks": risks,
        "poam-items": items,
    }}


# --------------------------------------------------------------------------- validation
def _py_compatible(schema):
    """OSCAL schemas use \\p{L} / \\p{N} Unicode classes that Python's `re` lacks; translate them."""
    if isinstance(schema, dict):
        return {k: (v.replace(r"\p{L}", "[^\\W\\d_]").replace(r"\p{N}", "\\d")
                    if k == "pattern" and isinstance(v, str) else _py_compatible(v))
                for k, v in schema.items()}
    if isinstance(schema, list):
        return [_py_compatible(x) for x in schema]
    return schema


def schema_errors(doc: dict, schema_file: str) -> list[str]:
    schema = _py_compatible(json.loads((ROOT / "schemas" / schema_file).read_text()))
    v = jsonschema.Draft7Validator(schema)
    return [f"{schema_file}: {'/'.join(map(str, e.absolute_path))}: {e.message[:200]}"
            for e in sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path))]


# --------------------------------------------------------------------------- markdown
def ssp_md(sysd, controls, baseline) -> str:
    s = sysd["system"]
    comp = {c["id"]: c["title"] for c in sysd["components"]}
    def status_of(stmts):
        states = {x["status"] for x in stmts}
        if states <= {"implemented", "not-applicable", "alternative"}:
            return "Implemented"
        return "Planned" if states == {"planned"} else "Partial"
    out = [f"# {s['name']} ({s['short_name']}) - System Security Plan summary", "",
           "Generated from `source/*.yaml` by `tools/build.py`. The authoritative machine-readable SSP is "
           "[`oscal/ssp.json`](../oscal/ssp.json). Fictional system for demonstration.", "",
           "## System characteristics", "",
           f"**Description.** {' '.join(s['description'].split())}", "",
           f"**Authorization boundary.** {' '.join(s['boundary'].split())}", "",
           f"**Network architecture.** {' '.join(s['network'].split())}", "",
           "## Security categorization (FIPS 199)", "",
           "| Information type | C | I | A |", "|---|---|---|---|"]
    for t in sysd["information_types"]:
        out.append(f"| {t['title']} | {t['c'].title()} | {t['i'].title()} | {t['a'].title()} |")
    worst = lambda k: max((t[k] for t in sysd["information_types"]), key=["low", "moderate", "high"].index).title()
    out += [f"| **System (high-water mark)** | **{worst('c')}** | **{worst('i')}** | **{worst('a')}** |", "",
            "## Control implementation", "",
            f"{len(controls)} controls from the NIST SP 800-53 Rev 5 MODERATE baseline.", "",
            "| Control | Title | Status | Components |", "|---|---|---|---|"]
    for cid, stmts in controls.items():
        out.append(f"| {cid} | {baseline[oscal_control_id(cid)]} | {status_of(stmts)} | "
                   f"{', '.join(dict.fromkeys(comp[x['component']] for x in stmts))} |")
    out += ["", "## Implementation statements", ""]
    for cid, stmts in controls.items():
        out.append(f"### {cid} {baseline[oscal_control_id(cid)]}")
        for x in stmts:
            out.append(f"- **{comp[x['component']]}** ({x['status']}): {' '.join(x['statement'].split())}")
        out.append("")
    return "\n".join(out)


def poam_md(poam) -> str:
    out = ["# Plan of Action and Milestones", "",
           "Generated by `tools/build.py`. Machine-readable version: [`oscal/poam.json`](../oscal/poam.json).", "",
           "| ID | Weakness | Controls | Risk | Detected | Scheduled completion | Owner |", "|---|---|---|---|---|---|---|"]
    for it in poam["items"]:
        out.append(f"| {it['id']} | {it['title']} | {', '.join(it['controls'])} | {it['risk'].title()} | "
                   f"{it['detected']} | {it['scheduled_completion']} | {it['owner']} |")
    out += ["", "## Milestones", ""]
    for it in poam["items"]:
        out.append(f"**{it['id']} {it['title']}**  ")
        out.append(f"Remediation: {it['remediation']}")
        out += [f"- {m['date']}: {m['text']}" for m in it["milestones"]]
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    sysd, controls, poam, baseline = load()
    errs = cross_check(sysd, controls, poam, baseline)
    if errs:
        print("\n".join(errs)); return 1
    ssp, pm = build_ssp(sysd, controls, baseline), build_poam(sysd, poam)
    errs = schema_errors(ssp, "oscal_ssp_schema.json") + schema_errors(pm, "oscal_poam_schema.json")
    if errs:
        print("\n".join(errs)); return 1

    outputs = {OUT_SSP: json.dumps(ssp, indent=2) + "\n", OUT_POAM: json.dumps(pm, indent=2) + "\n",
               OUT_SSP_MD: ssp_md(sysd, controls, baseline), OUT_POAM_MD: poam_md(poam)}
    if args.check:
        stale = [p.relative_to(ROOT).as_posix() for p, c in outputs.items() if not p.exists() or p.read_text() != c]
        if stale:
            print("Generated files are out of date, run python tools/build.py:", ", ".join(stale)); return 1
    else:
        for p, c in outputs.items():
            p.parent.mkdir(exist_ok=True); p.write_text(c)
    n_open = sum(any(x["status"] in OPEN_STATES for x in v) for v in controls.values())
    print(f"OK: {len(controls)} controls ({len(controls) - n_open} fully implemented, {n_open} with open items), "
          f"{len(poam['items'])} POA&M items; SSP and POA&M valid against OSCAL {OSCAL_VERSION} schemas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
