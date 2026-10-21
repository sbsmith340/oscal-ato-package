import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402

SYS, CONTROLS, POAM, BASELINE = build.load()


def test_sources_cross_check_clean():
    assert build.cross_check(SYS, CONTROLS, POAM, BASELINE) == []


def test_generated_documents_valid_against_official_schemas():
    assert build.schema_errors(build.build_ssp(SYS, CONTROLS, BASELINE), "oscal_ssp_schema.json") == []
    assert build.schema_errors(build.build_poam(SYS, POAM), "oscal_poam_schema.json") == []


def test_schema_validation_actually_rejects_bad_documents():
    ssp = build.build_ssp(SYS, CONTROLS, BASELINE)
    del ssp["system-security-plan"]["metadata"]["title"]
    assert any("'title' is a required property" in e for e in build.schema_errors(ssp, "oscal_ssp_schema.json"))


def test_control_id_conversion():
    assert build.oscal_control_id("AC-2") == "ac-2"
    assert build.oscal_control_id("AC-2(3)") == "ac-2.3"
    assert build.oscal_control_id("IA-2(12)") == "ia-2.12"


def test_control_outside_moderate_baseline_rejected():
    c = copy.deepcopy(CONTROLS)
    c["AC-2(11)"] = [{"component": "entra-id", "status": "implemented", "statement": "x"}]  # High-only enhancement
    assert any("not in the NIST" in e for e in build.cross_check(SYS, c, POAM, BASELINE))


def test_partial_control_without_poam_item_rejected():
    c = copy.deepcopy(CONTROLS)
    c["AC-6"][0]["status"] = "partial"
    assert any("AC-6: partial/planned in the SSP but has no POA&M item" in e for e in build.cross_check(SYS, c, POAM, BASELINE))


def test_poam_item_for_implemented_control_rejected():
    p = copy.deepcopy(POAM)
    p["items"][0]["controls"] = ["SC-8"]
    assert any("not partial/planned" in e for e in build.cross_check(SYS, CONTROLS, p, BASELINE))


def test_uuids_are_deterministic_and_unique():
    a = json.dumps(build.build_ssp(SYS, CONTROLS, BASELINE))
    b = json.dumps(build.build_ssp(SYS, CONTROLS, BASELINE))
    assert a == b
    import re
    uuids = re.findall(r'"uuid": "([0-9a-f-]{36})"', a)
    assert len(uuids) == len(set(uuids))


def test_impact_level_is_high_water_mark():
    sil = build.build_ssp(SYS, CONTROLS, BASELINE)["system-security-plan"]["system-characteristics"]["security-impact-level"]
    assert sil == {"security-objective-confidentiality": "fips-199-moderate",
                   "security-objective-integrity": "fips-199-moderate",
                   "security-objective-availability": "fips-199-moderate"}


def test_committed_outputs_are_current():
    assert (ROOT / "oscal" / "ssp.json").read_text() == json.dumps(build.build_ssp(SYS, CONTROLS, BASELINE), indent=2) + "\n"


def test_summary_status_labels():
    md = build.ssp_md(SYS, CONTROLS, BASELINE)
    row = lambda cid: next(l for l in md.splitlines() if l.startswith(f"| {cid} |"))
    assert "| Partial |" in row("AU-11")      # single partial statement
    assert "| Partial |" in row("RA-5")       # implemented + planned
    assert "| Implemented |" in row("SC-8")
