# Changelog

## 0.2.4

- Add `AECO_STUDY_ROOT` (default `/`). Suite hooks put tests and both result
  routes under `/Studies/clash/Clash`, with exact/twin materials shared at
  `/Studies/clash/ExactMaterials` and cameras under `/Renders/clash`.
- Rebase copies of input and exact layers, preserving relationship targets,
  shader connections, internal prototype references and path metadata. Keep
  the project catalog in place; author no additional root catalog.
- Discover tests from saved stage data. The CLI accepts a unique test name,
  an absolute path, or an omitted `--test` for a stage with one test.
- Verify the full v0.5.2 delivery and the pinned v0.4.8 native hook with a
  non-default root. All 47 tests pass; committed example assets retain their
  bytes and the default example still passes all 48 family checks.
- Deviations: BCF export remains unimplemented. The full-delivery test uses
  retained exact layers and remeasures them natively; fresh exact production
  remains tied to v0.4.8. One Nix attempt stopped at the IFC tag's HTTP 404;
  no retry. See [acceptance evidence](docs/acceptance.md).

## 0.2.3

- public re-pin: toolchain v0.3.10, core v0.9.5, axis v0.1.5,
  datacentre v0.4.8, solid v0.1.5, IFC v0.2.2, usdSolid v0.1.5,
  usdSolidOcct v0.1.4. Record the checked forge revisions alongside tags;
  keep compatible requirement ranges unchanged.
- Import the bridge's package outputs from its source pin with the selected
  schema and shared toolchain inputs; ignore the generated example source alias.
- Align the source package version with the library and distribution version.
- Republish the pinned example: crate and nine own layers retain 2,806,460
  bytes; source hashes and findings match. Retain all six committed PNGs
  after five fresh renders; update the source-pin notice and manifest receipts.
- Verify 48 checks, 0 failed, 0 not run; 29 structure rules and 37 tests pass.
- Deviations: native checks use bridge v0.1.4 with schema/validators v0.1.4;
  the selected usdSolid v0.1.5 native build remains unproven. The single offline
  Nix check rejected a shallow local override before evaluation; no retry.
  See [acceptance evidence](docs/acceptance.md).

## 0.2.2

- public names → github.com/criad-com.
- Pin toolchain v0.3.8; retain all other dependency refs and requirement ranges.
- Update the manifest toolchain receipt; retain committed USD and image bytes.
- Verify 48 checks, 0 failed, 0 not run; 29 structure rules and 37 tests pass.
- Nix remains not proven: one attempt stopped at a nested toolchain input
  with HTTP 404.

## 0.2.1

- Re-pin to train aeco-0.7.0: toolchain v0.3.5, axis v0.1.2,
  datacentre v0.4.5 and solid v0.1.2; retain compatible requirement ranges.
- Verify 47 checks, 0 failed, 0 not run; 28 structure rules and 37 tests pass.
  Refresh the source-pin receipt only; all USD files and images retain their bytes.
- Nix remains not proven: one offline attempt could not resolve the nested
  build-toolchain input.

## 0.2.0

- Add exact common-volume and separation measurements through the isolated
  usdSolidOcct runtime, retaining kernel tolerance and both body stamps.
- Compare mesh and exact per pair, with explicit uncertainty and decided-by
  columns; add the ClashRouteDisagreement validator and seeded regression.
- Pin clash v0.4.4 and toolchain v0.3.3; reproduce the 5 mm uncertain mesh gap
  and false tangent penetration against the source manifest.
- Publish both result layers, two exact tessellation studies and Route S
  wireframe; preserve the stock-USD standalone result contract.

## 0.1.0

- Add codeless clash test/result records and three Python UsdValidation rules.
- Measure triangle intersections, containment and edge/face gaps after an AABB
  prefilter; author deterministic findings and framing cameras separately.
- Preserve uncertainty provenance, editable review overlays and explicit NOT RUN
  exact comparisons; leave exact-only volume unauthored.
- Publish the pinned clash example and two conditional deflection studies with
  standalone USD and stock-USD renders.
- Record the source-fixture verdict mismatch and conditional error estimates.
