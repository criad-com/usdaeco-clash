# Acceptance evidence for v0.2.3

All eight direct family inputs use the public release tags in
[dependencies.json](../dependencies.json), with their checked forge revisions.
Core remains supported by `>=0.9.2,<1.0`; the Python toolchain range remains
`>=0.3.3,<0.4`. Neither range needed widening. The source package, distribution,
library and generated resource plugin all report 0.2.3.

| Acceptance | Measured result | Status |
|---|---|---|
| Family gate | 48 checks, 0 failed, 0 not run | PASS |
| Structure under toolchain v0.3.10 | S01–S29: 29 rules, 0 failed | PASS |
| Pytest | 37 passed, including native geometry regressions | PASS |
| Direct source pins | 8 tags and 8 checked forge revisions agree | PASS |
| Release metadata | 4 version declarations agree on 0.2.3 | PASS |
| Public flake references | 8 release-tag URLs; 0 legacy public references or family hash refs | PASS |
| Validation plugins | 8 core + 4 clash rules loaded; published stage 0 errors, 10 warnings | PASS |
| Fresh pinned example | Findings and comparison match; 12,411 plugin-free prims; 4 nonblank views | PASS |
| Published USD | Flattened crate + 9 own layers: all 2,806,460 bytes unchanged | PASS |
| Source evidence | All 3 source layer hashes and the source manifest hash unchanged | PASS |
| Images | 5 fresh 1280×800 renders; all 6 committed PNGs retain their bytes | PASS |
| Exact comparison | 3 mesh + 3 exact pairs; 5 mm clearance decided only by exact; 0 unclassified | PASS |
| Publication sweep | 69 files, 0 findings, including binary USD and image metadata | PASS |
| Nix syntax | Flake parses successfully | PASS |
| Nix flake check | 1 offline attempt, exit 1 during local override resolution | NOT PROVEN |

Run the commands in the [README](../README.md), including
`examples/datacentre/run.py --publish`. Publication regenerated the source IFC,
exact bodies, both result layers, tessellation studies, wireframe, flattened
crate and five renders. The full gate then reproduced the example in 40.193 s
against its 180 s budget. No expected findings or comparison table changed.
The [machine-readable evidence](public-repin.json) records artifact hashes,
render differences and the observed native runtime.

The final result diff changes only the source-pin notice and manifest receipts.
Geometry, derived layers, cameras, schema definitions and committed images
retain their bytes. Producer stamps identify the unchanged derivation
implementations and remain unchanged. Upstream [datacentre 0.4.8](https://github.com/criad-com/usdaeco-datacentre/blob/v0.4.8/CHANGELOG.md)
retains published stage and camera bytes, while [bridge 0.1.4](https://github.com/criad-com/usdSolidOcct/blob/v0.1.4/CHANGELOG.md)
records unchanged exported geometry after its native rebuild.

## Deviations

- **Native package substitution.** The observed bridge is v0.1.4, with schema
  and validators v0.1.4, verified against that release's runtime receipt.
  The selected usdSolid source is v0.1.5. Its [changelog](https://github.com/criad-com/usdSolid/blob/v0.1.5/CHANGELOG.md)
  records builder/pin changes and a pending native rebuild, with unchanged
  upstream geometry sources. The flake wires v0.1.5 into the bridge build;
  native execution of that exact package combination remains not proven.
- **Nix setup failure.** The single `nix flake check --offline --no-write-lock-file`
  attempt used local overrides for all eight direct pins, the tagged build
  toolchain and the toolchain's historical core fixture. Remote builders and
  substituters were disabled. The local build-toolchain clone was shallow,
  but its Git URL omitted Nix's required shallow option. Nix rejected the
  override before output evaluation or derivation checks. This was an override
  setup error, not evidence about public resolution. No retry was made;
  public online resolution and the complete build remain not proven.
- **Render sampling.** Five fresh PNGs passed the nonblank and size checks.
  Their largest mean absolute channel difference from the committed images was
  0.097370 on the 0–255 scale. The committed PNGs were retained, and their
  receipts were regenerated after publication; S28 checks freshness by rendering,
  without requiring PNG byte equality across runs.
- **Finding order.** The raw generated-findings hash changed because validator
  findings arrived in a different order. The complete findings multiset matches
  the expected JSON exactly; the comparison Markdown is byte-identical.

## Historical v0.2.0 evidence

Measured against core v0.9.2, toolchain v0.3.3, datacentre v0.4.4,
solid v0.1.0, IFC integration v0.2.0 and usdSolid/usdSolidOcct v0.1.0. The family
checks use USD 26.8; native operations run in the bridge's separate runtime.
Axis v0.1.1 is a compatibility pin, not loaded by either engine.

| Acceptance | Measured result | Status |
|---|---|---|
| Mesh results | 3: 2 nominal hard, 1 nominal clearance; 0 unclassified | PASS |
| Exact results | 3 measured pairs: hard, clearance, touching; 2 non-touching findings | PASS |
| Through-wall pair | Mesh −75.000003 mm; exact common volume 0.000428366761192 m³ | PASS |
| 5 mm clearance decided only by exact | Mesh 5.000114 mm inside 5.7582 mm band; exact 5.000000 mm with 0.020 mm band | PASS |
| False mesh penetration | Mesh −1.063541 mm inside 1.0636 mm band; exact touching, zero common volume | PASS |
| Comparison table | 3 paired rows match expected Markdown; both routes match expected JSON | PASS |
| Manifest assertions | All 3 axes, radii, side counts, signed distances, bands and source witnesses checked | PASS |
| Exact export | 5 selected products, 5 valid exact bodies, 0 failures | PASS |
| Two deflections | 0.1 / 6 mm requested; pipe 228 / 124 triangles; tray 12 / 12 | PASS |
| Family gate | 47 checks, 0 failed, 0 not run | PASS |
| Structure and sanitization | 28 checks, 0 failed; term sweep clean | PASS |
| Pytest | 37 passed, including all 4 validator seeded-defect tests and native geometry regressions | PASS |
| Real validation plugins | 8 core + 4 clash rules loaded; published stage 0 errors, 10 warnings | PASS |
| Missing-core guard | Missing core import exits 1 with an explicit failure | PASS |
| Standalone result | 12,411 prims; 2,871,783 bytes; relocated plugin-free composition has 0 errors | PASS |
| Renders | 4 views plus vanilla proof, 1280×800; largest committed view 131,810 bytes | PASS |
| Nix | One attempt stopped at nested input resolution before derivation checks | NOT PROVEN |

The ten warnings are two source classification warnings, six new-result review
warnings and two mesh-uncertainty warnings. No route-disagreement warning is
expected: the fixture differences are inside the mesh bands. The deliberately
contradictory seeded test does produce that warning.

Source counts are read from the pinned manifest and checked against the stage;
no base-variant counts are substituted. Native tests independently verify hard
volume against the analytic cylinder/partition intersection, preserve distance
and volume under shared rotation/translation, and remove a pair after moving
the pipe. Other tests reject invalid evidence and distinguish absent runtimes
from broken ones. Result authoring preserves review opinions and deterministic
paths/bytes. A nested element cannot substitute its mesh for its parent's twin.

### Deviations

- **Result count.** Exact retains the tangent as a third touching result so all
  three pairs appear in the comparison. There are two non-touching exact findings,
  rather than silently dropping the third measured pair.
- **Kernel distance semantics.** BRepExtrema returns unsigned separation and zero
  for overlap. The exact result records negative zero and uses Boolean common
  volume for hard clashes. A signed penetration magnitude is not available and
  is not invented. The bridge exposes no extrema witness: the exact point is
  labelled as a camera-framing midpoint in evidence.
- **Tolerance spelling.** `aeco:body:tolerance` is accepted first. The pinned
  exporter authors core's canonical `aeco:derived:tolerance`, used otherwise.
  The pair uncertainty is the sum of both bodies' kernel tolerances.
- **Test-record inheritance.** The existing explicit `AecoClashTest :
  AecoGroupBase` contract remains an exception to E1/E5's group restriction.
  It adds a coordination record, no product kind or spatial hierarchy.
- **Tessellation study.** The two requested linear deflections also use the
  bridge's 0.5 radian angular limit. They change triangle counts but produce
  similar measured clearances. Requested deflection is not claimed as the
  measured maximum error or as the original Route K tessellation.
- **Nix resolution.** The single offline attempt stopped while resolving
  `core/datacentre` at v0.4.1 with HTTP 404. The missing `follows` connection was
  added; no second attempt was made. Nix evaluation/build remains not proven.
- **Scope.** One Brep per BodyExact and rigid/uniform affine transforms are
  supported. If placement makes kernel tolerance exceed the authored world
  bound, the operation fails. Multi-body results name the selected body pair;
  common volume is not an aggregated union over an assembly.

### Remaining work

Resolve Nix inputs and prove its derivation checks in a later run. Certified
penetration depth, extrema witnesses, BCF export, multi-Brep arrays and
whole-facility acceleration are future work. The three planted comparison
cases and their exact results are reproduced in this release.
