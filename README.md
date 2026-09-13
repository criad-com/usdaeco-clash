# usdAecoClash — mesh and exact clash evidence with measured uncertainty

## Use case

Check two collections of core elements using tessellated or exact bodies.
Keep each route's measurements, uncertainty and review status in separate USD
layers. The [walkthrough](docs/usecase.md) explains the measured comparison.

## The schema on an index card

| Schema | Inherits / fallback | Contract |
|---|---|---|
| `AecoClashTest` | `AecoGroupBase` / `Scope` | method, tolerance, clearance; `setA` / `setB` collections |
| `AecoClashResult` | `Typed` / `Scope` | two elements, kind, distance, volume, point, uncertainty, status, evidence |

Properties use `aeco:clash:`. Measurements are derived; settings and review
status are drivers. The existing test-record inheritance exception is documented
in the walkthrough. No product-kind vocabulary or new applied API is added.

## The example

Open [result/example.usdc](examples/datacentre/result/example.usdc) in a USD
viewer. It is flattened and self-contained. The pinned `clash` v0.4.8 example
has three mesh and three exact results, including exact touching. The **5.000 mm
gap is decided only by exact**: its mesh uncertainty is 5.7582 mm. The tangent's
1.06354 mm mesh penetration is also inside its band; exact reports touching.
Both routes find the through-wall clash, with exact common volume
**0.000428366761 m³**. See the [complete table](examples/datacentre/expected/compare.md).

![Clash results from above](examples/datacentre/renders/overview.png)

## Build and check

Use the family Python with OpenUSD, UsdValidation, NumPy, IfcOpenShell 0.8.5,
PyYAML, pytest, Jinja2 and Pillow. Tests import source directly; no editable
installation or setuptools is needed. Set `PYTHON` to that interpreter and
configure sibling checkouts at the tags in the Family table:

```sh
export PYTHON=python3
export CORE_DIR="$(cd ../usdaeco-core && pwd)"
export CORE_PLUGIN_DIR="$CORE_DIR/out/plugins/usdAeco/resources"
export TOOLCHAIN_DIR="$(cd ../usdaeco-toolchain && pwd)"
export AECO_DATACENTRE_ROOT="$(cd ../usdaeco-datacentre && pwd)"
export AECO_IFC_ROOT="$(cd ../usdaeco-ifc && pwd)"
export AECO_SOLID_ROOT="$(cd ../usdaeco-solid && pwd)"
export USD_SOLID_OCCT_RUNTIME="$(pwd)/../usdSolidOcct/result-runtime"
export PXR_PLUGINPATH_NAME="$CORE_PLUGIN_DIR:$PWD/usdAecoClash"
export PYTHONDONTWRITEBYTECODE=1
env -u PYTHONPATH bash build.sh
env -u PYTHONPATH PYTHONPATH="$CORE_DIR:$PWD" "$PYTHON" check.py
env -u PYTHONPATH "$PYTHON" -m pytest -q
env -u PYTHONPATH "$PYTHON" examples/datacentre/run.py --publish
```

`check.py` prints `N checks, M failed, K not run`, including all 29 structure
rules. Missing core validator imports fail loudly. The exact engine launches
the runtime's ABI-matched Python; the family Python never loads its libraries.
The IFC companion compiles its existing small adapter into this checkout's
`.work/` using a C++ compiler. No sibling checkout is modified. The runtime's
stock renderer is selected automatically, or set `USDRECORD` explicitly.
An absent runtime produces NOT RUN; a present but broken runtime fails.

Run the CLI against the published stage, which carries both representations:

```sh
env -u PYTHONPATH "$PYTHON" tools/run_clash.py run examples/datacentre/result/example.usdc --test /Clash/Pinned --method mesh --output out/mesh.usda --json out/mesh.json
env -u PYTHONPATH "$PYTHON" tools/run_clash.py run examples/datacentre/result/example.usdc --test /Clash/Pinned --method exact --output out/exact.usda --json out/exact.json
env -u PYTHONPATH "$PYTHON" tools/run_clash.py compare out/mesh.json --exact out/exact.json
```

The installed entry point is `aeco-clash`. Compose outputs above the source;
replace the previous layer on recheck so disappeared pairs do not persist.
`--method` overrides the driver for this run without editing the input.

Set `AECO_STUDY_ROOT=/Studies/clash` when invoking the hook for a suite stage.
The hook copies and scopes its input layers, writes tests/results beneath
`<root>/Clash`, and places exact and twin materials together at
`<root>/ExactMaterials`. Cameras use `/Renders/clash/<camera>`; `/Studies`
is a plain Scope. The project and its catalog retain their existing paths.
The default `/` preserves the committed standalone example, including its
historical camera layout.

Saved stages carry their root in metadata and test paths. Consumers discover
it even after the environment changes: omit `--test` for a single-test stage,
use `--test Pinned` for a unique name, or supply the actual absolute path.
`generate_inputs.py --out <directory>` also honors the study root.
See the [integration notes](examples/datacentre/README.md) for full-delivery
manifests and retained exact layers.

Flake URLs use public repository names. Supply deployment mirrors through an
external registry or `--override-input`, following the
[toolchain instructions](https://github.com/criad-com/usdaeco-toolchain/blob/v0.3.10/docs/repo-conventions.md),
then run `nix flake check`. Never commit deployment-specific lockfiles.

## Family

| Dependency | Tested pin | Role |
|---|---|---|
| core | v0.9.5; supports `>=0.9.2,<1.0` | identity, collections, representation mark |
| axis | v0.1.5 | family compatibility pin |
| toolchain | v0.3.10 | generation, structure, examples and rendering |
| datacentre | v0.4.8 | published clash fixture and source generator |
| solid | v0.1.5 | exact-body conventions and wireframe display |
| IFC integration | v0.2.2 | optional exact export and native runtime launcher |
| usdSolid | v0.1.5 | optional BrepArray schema |
| usdSolidOcct | v0.1.4 | optional OCCT bridge source |

The schema requires only core. Exact runtime dependencies are optional companion
inputs, recorded in [dependencies.json](dependencies.json).
[Family board](https://github.com/criad-com/usdaeco-board).

## Layout

`usdAecoClash/` contains the codeless schema and user documentation.
`usdAecoClashValidators/` registers four Python validators.
`tools/usdaeco_clash/`, `testenv/`, `conformance/`, `docs/` and
`examples/datacentre/` contain the engines, tests, profile, story and results.

## Status

Version 0.2.4: **48 checks, 0 failed, 0 not run; structure 29/0; 47 tests passed**.
Scoped hooks pass on the pinned clash fixture and full v0.5.2 delivery;
committed example assets remain byte-identical. Nix remains not proven: the
single attempt stopped at the IFC v0.2.2 public tag with HTTP 404.
Native checks use bridge v0.1.4 with schema/validators v0.1.4;
the selected usdSolid v0.1.5 native build remains unproven.
The [acceptance report](docs/acceptance.md) records checks,
measurements and deviations. Exact common volume and clearance are measured;
exact penetration depth, BCF export and whole-facility performance remain
unproven. Exact touching is retained as a third comparison result.

## Licence

MIT. See [LICENSE](LICENSE).

Dependencies retain their licences: OpenUSD and UsdSolid retain
upstream notices; OCCT is LGPL-2.1 with its exception, dynamically linked;
IfcOpenShell is LGPL-3.0, NumPy and Jinja2 are BSD-3-Clause, and Pillow is HPND.
