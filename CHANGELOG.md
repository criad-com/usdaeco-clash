# Changelog

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
