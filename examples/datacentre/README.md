# Three pairs measured by mesh and exact

The source is demo-datacentre-01, clash v0.4.5. Follow the environment setup in
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
