# Acceptance evidence for v0.2.2

Public names now use `github.com/criad-com`. The checks used toolchain v0.3.8
and the exact dependency releases recorded in `dependencies.json`: core v0.9.2,
axis v0.1.2, datacentre v0.4.5, solid v0.1.2, IFC integration v0.2.0 and
usdSolid/usdSolidOcct v0.1.0. Tests import source without setuptools.

| Acceptance | Measured result | Status |
|---|---|---|
| Family gate | 48 checks, 0 failed, 0 not run | PASS |
| Structure under toolchain v0.3.8 | 29 rules, 0 failed, including S05 and S25 | PASS |
| Pytest | 37 passed | PASS |
| Public references | 10 references rewritten; 0 legacy public references remain | PASS |
| Release metadata | Library, Python package and resource plugin agree on 0.2.2 | PASS |
| Dependency refs | Only toolchain changed, from v0.3.5 to v0.3.8 | PASS |
| Validation plugins | 8 core + 4 clash rules loaded; published stage 0 errors, 10 warnings | PASS |
| Fresh pinned example | Findings and comparison match; 12,411 plugin-free prims; 4 non-blank views | PASS |
| Published artifacts | Committed USD, renders and user documentation assets unchanged | PASS |
| Nix | One attempt stopped during nested input resolution with HTTP 404 | NOT PROVEN |

## Deviations

- The single `nix flake check --offline --no-write-lock-file` attempt used
  local copies of the declared direct pins, then failed to resolve
  `toolchain/aeco-toolchain` at revision
  `e190680d3f94eb76e06abe77574fda1308af2c85` from its public source (HTTP 404).
  Derivation checks did not run; no second attempt was made.
- The example manifest's toolchain receipt was updated to satisfy S22's exact
  pin agreement. No result was republished, and no source or artifact hashes
  changed.

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
