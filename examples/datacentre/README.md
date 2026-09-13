# Three pairs measured by mesh and exact

The source is demo-datacentre-01, clash v0.4.8. Follow the environment setup in
the [root README](../../README.md), then run:

```sh
env -u PYTHONPATH "$PYTHON" examples/datacentre/run.py
env -u PYTHONPATH "$PYTHON" examples/datacentre/run.py --publish
```

Ordinary runs write `out/`. Publication refreshes `result/`, `renders/` and
`manifest.json`; expected findings remain separately reviewed. Counts and
geometric expectations come from the pinned `dc.manifest.json`. The five
selected products are regenerated through the IFC exact exporter in this
checkout's `.work/`; sibling inputs are read-only. `generate_inputs.py`
regenerates this checkout's collections and cameras.

Open `result/example.usdc` directly in stock USD. The flattened crate includes
source bodies, exact bodies, twins and results. Original own layers are archived
under `result/layers/`, including `exact-results.usda`, `deflection-study.usda`
and `wireframe-view.usda`. `result/vanilla.png` proves plugin-free rendering.

| View | Meaning |
|---|---|
| overview | Original meshes: red nominal hard, amber nominal clearance; grey partners |
| fine | Exact-body tessellation at 0.1 mm requested linear deflection |
| coarse | Same bodies at 6 mm requested linear deflection |
| wireframe | Exact edge guides over their Mesh twins, viewed obliquely |

`out/mesh.json` and `out/exact.json` contain engine records. `out/compare.md`
comes from the comparison CLI and must match [expected/compare.md](expected/compare.md).
The mesh has three findings, but the 5 mm gap and apparent tangent penetration
are inside its bands. Exact reports hard, clearance and touching. All six have
known finding kinds. See [the measured analysis](../../docs/usecase.md).

## Suite integration

Set `AECO_STUDY_ROOT=/Studies/clash` before `derive(stage, out_dir)`.
Its standalone tests and input cameras are copied into the output directory
and their sublayer entries replaced; the source layers remain unchanged.
Alternatively generate scoped inputs directly with
`generate_inputs.py --out <scratch-inputs>`. Tests/results use `<root>/Clash`,
materials use `<root>/ExactMaterials`, and cameras use `/Renders/clash`.
No catalog classes are added by this hook; the project catalog stays in place.

Set `AECO_DATACENTRE_STAGE` to the full delivery's `dc.usda` to read its adjacent
`dc.manifest.json` for the source census and geometric witnesses. Fresh exact
production still uses the v0.4.8 source recipe in `AECO_DATACENTRE_ROOT`.
The v0.5.2 full-delivery regression exercises the mesh hook, composes copies of
the retained exact layers, and remeasures the exact findings in the native runtime.

When retaining exact opinions in a suite, copy `exact.usda`, `twins.usda` and
`exact-results.usda` into its output directory, call
`usdaeco_clash.paths.scope_layer(layer, study_root)` on each writable copy,
save it, and compose the copies. This moves material bindings, shader connections,
internal prototype references and result cameras as well as their prims.
Archive the hook's resulting sublayer stack so the original standalone inputs
are not composed again.

Exact bodies and their mesh twins share the producing library's material set:
`/Studies/clash/ExactMaterials`. The solid library can use the same relative
name under `/Studies/solid`; those sets do not collide. The default `/` keeps
all committed example bytes, including its historical cameras, unchanged.
The shared example harness compares against those default-root expectations;
use the hook and scoped regression tests for suite roots.
