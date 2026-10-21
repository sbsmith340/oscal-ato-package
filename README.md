# OSCAL ATO Package

> A System Security Plan and Plan of Action and Milestones for a fictional federal cloud system, written as **compliance as code**. Human-editable YAML builds into NIST **OSCAL 1.1.2** JSON, which is validated against the official NIST schemas and checked against the real NIST SP 800-53 Rev 5 Moderate baseline on every commit.

![ci](https://github.com/sbsmith340/oscal-ato-package/actions/workflows/ci.yml/badge.svg)
![oscal](https://img.shields.io/badge/OSCAL-1.1.2-1f6feb)
![baseline](https://img.shields.io/badge/NIST%20800--53%20Rev%205-Moderate-blue)

## Problem
Authorization packages are usually Word documents and spreadsheets. They drift out of date the day after the assessment, can't be checked automatically, and make it easy to claim a control is implemented while the POA&M says otherwise. FedRAMP and agencies are moving to **OSCAL**, NIST's machine-readable format for security documentation, so packages can be validated and exchanged by tools instead of by email.

## What's in the package
| Artifact | What it is |
|---|---|
| [`oscal/ssp.json`](oscal/ssp.json) | OSCAL System Security Plan: system characteristics, FIPS 199 categorization, authorization boundary, network and data flow, users, components, and control implementations |
| [`oscal/poam.json`](oscal/poam.json) | OSCAL POA&M: observations, risks, remediation plans, and dated milestones |
| [`docs/SSP.md`](docs/SSP.md) / [`docs/POAM.md`](docs/POAM.md) | Readable summaries generated from the same source |
| [`source/*.yaml`](source/) | The only files a person edits: system description, control statements, POA&M items |
| [`tools/build.py`](tools/build.py) | Builds, cross-checks, validates, and renders everything |

**The system:** the *Field Inspection Portal*, a fictional Moderate-impact web application on Azure. It uses Front Door with WAF, App Service, Azure SQL over a private endpoint with a customer-managed key, Key Vault, Entra ID with PIM and phishing-resistant MFA, and Sentinel plus Defender for Cloud as leveraged services.

**Control coverage:** 24 controls from the Moderate baseline across AC, AU, CA, CM, CP, IA, IR, RA, SC, and SI. 18 are fully implemented and 6 have open items, each tracked in the POA&M:

| POA&M | Weakness | Control | Risk |
|---|---|---|---|
| POAM-001 | Audit log retention below the one-year requirement | AU-11 | Moderate |
| POAM-002 | No automated configuration drift detection | CM-6 | Moderate |
| POAM-003 | Backup restore never tested | CP-9 | High |
| POAM-004 | Incident reporting to CISA not exercised | IR-6 | Moderate |
| POAM-005 | No dependency or container scanning in the pipeline | RA-5 | Moderate |
| POAM-006 | Behavior analytics not enabled | SI-4 | Low |

## What the build enforces
The build fails if any of these are true:
1. **A control isn't in the Moderate baseline.** Control IDs are checked against a list extracted from NIST's own [oscal-content](https://github.com/usnistgov/oscal-content) baseline profile (`baseline/moderate-baseline.json`), so a typo or a High-only enhancement can't slip in.
2. **The SSP and POA&M disagree.** Every control marked *partial* or *planned* must have a POA&M item, and every POA&M item must point at a control that is actually partial or planned. This is the most common inconsistency in real packages.
3. **A statement references a component** that isn't defined in the system inventory.
4. **A milestone schedule doesn't line up.** The last milestone date must equal the scheduled completion date.
5. **Either document fails the official NIST OSCAL 1.1.2 JSON schema** (vendored in `schemas/`).

UUIDs are generated deterministically, so rebuilding produces identical files and diffs show only real changes.

## How to run it
```bash
git clone https://github.com/sbsmith340/oscal-ato-package.git
cd oscal-ato-package
pip install pyyaml jsonschema pytest
python tools/build.py          # builds oscal/*.json and docs/*.md, validates everything
pytest -q tests                # 11 tests
```
To change the package, edit `source/*.yaml` and rebuild. CI rejects a commit if the generated files weren't rebuilt.

## Design notes
- **YAML in, OSCAL out.** OSCAL JSON is verbose and full of UUIDs, which is fine for tools but bad for human review. Writing the source in YAML keeps pull-request diffs readable while the output stays standards-compliant.
- **Leveraged services are named, not owned.** Entra ID, Sentinel, and Defender for Cloud sit outside the boundary, as FedRAMP-authorized services. Statements say how the system *uses* them, which is how inheritance is described in real packages.
- **Honest status.** Six controls are deliberately left partial or planned. A package showing 100% implemented is a red flag to an assessor.
- **Schema regex compatibility.** NIST's schemas use `\p{L}` / `\p{N}` Unicode classes that Python's `re` module doesn't support. The validator translates them to equivalent classes before validating, and a test confirms the validator still rejects malformed documents.

## Framework mapping
| Process | Supported by |
|---|---|
| RMF Step 2 *Categorize* (FIPS 199, SP 800-60) | Information types with C/I/A impact and a high-water mark |
| RMF Step 3 *Select* / Step 4 *Implement* | Baseline-checked control selection and component-level implementation statements |
| RMF Step 6 *Authorize* | SSP + POA&M, the core of an authorization package |
| RMF Step 7 *Monitor* (CA-5, CA-7) | Machine-readable POA&M with dated milestones |

## Limitations & what's next
- Covers 24 of the 287 Moderate controls. Add the rest incrementally, by family.
- Add a Security Assessment Plan / Security Assessment Results (OSCAL `assessment-plan` / `assessment-results`)
- Validate against FedRAMP-specific constraints (FedRAMP namespace props, required attachments)
- Render a printable SSP document from the OSCAL JSON

## Repo layout
```
source/        system.yaml, controls.yaml, poam.yaml   <- edit these
tools/         build.py
oscal/         ssp.json, poam.json                      <- generated
docs/          SSP.md, POAM.md                          <- generated
schemas/       official NIST OSCAL 1.1.2 JSON schemas
baseline/      NIST SP 800-53 Rev 5 MODERATE control IDs and titles
tests/
```

---
The Field Inspection Portal, its agency, and its contractor are fictional. NIST schemas and baseline data come from [usnistgov/OSCAL](https://github.com/usnistgov/OSCAL) and [usnistgov/oscal-content](https://github.com/usnistgov/oscal-content). Built by [Shawn Smith](https://sbsmith340.github.io).
