{
  description = "usdAecoClash semantic library and example";
  inputs = {
    toolchain.url = "github:criad-com/usdaeco-toolchain?ref=v0.3.8";
    nixpkgs.follows = "toolchain/nixpkgs";
    core.url = "github:criad-com/usdaeco-core?ref=v0.9.2";
    core.inputs.toolchain.follows = "toolchain";
    core.inputs.nixpkgs.follows = "nixpkgs";
    core.inputs.datacentre.follows = "datacentre";
    axis.url = "github:criad-com/usdaeco-axis?ref=v0.1.2";
    axis.inputs.core.follows = "core";
    axis.inputs.toolchain.follows = "toolchain";
    axis.inputs.nixpkgs.follows = "nixpkgs";
    axis.inputs.datacentre.follows = "datacentre";
    datacentre.url = "github:criad-com/usdaeco-datacentre?ref=v0.4.5";
    datacentre.flake = false;
    solid.url = "github:criad-com/usdaeco-solid?ref=v0.1.2";
    solid.flake = false;
    ifc.url = "github:criad-com/usdaeco-ifc?ref=v0.2.0";
    ifc.flake = false;
    usdSolid.url = "github:criad-com/usdSolid?ref=v0.1.0";
    usdSolid.inputs.aeco-toolchain.follows = "usdSolidOcct/aeco-toolchain";
    usdSolid.inputs.usdaeco-toolchain.follows = "toolchain";
    usdSolid.inputs.upstream.follows = "usdSolidOcct/upstream";
    usdSolidOcct.url = "github:criad-com/usdSolidOcct?ref=v0.1.0";
    usdSolidOcct.inputs.usdSolid.follows = "usdSolid";
    usdSolidOcct.inputs.usdaeco-toolchain.follows = "toolchain";

  };
  outputs = { self, nixpkgs, toolchain, core, axis, datacentre, solid, ifc, usdSolid, usdSolidOcct }:
    let
      eachSystem = nixpkgs.lib.genAttrs [ "aarch64-darwin" "x86_64-linux" ];
      forSystem = system:
        let
          kit = toolchain.lib.forSystem system;
          pkgs = nixpkgs.legacyPackages.${system};
          corePlugin = core.packages.${system}.default;
          schema = (kit.buildCodelessSchema { name = "usdAecoClash"; src = self; deps = [ corePlugin ]; }).overrideAttrs (old: {
            postInstall = (old.postInstall or "") + ''
              cp -RL tools/usdaeco_clash "$out/python/"
            '';
          });
          plugins = kit.pluginSet { plugins = [ schema ]; };
          setup = ''
            export TOOLCHAIN_DIR=${toolchain}
            export CORE_DIR=${core}
            export CORE_PLUGIN_DIR=${corePlugin}/plugins/usdAeco/resources
            export AECO_IFC_ROOT=${ifc}
            export AECO_SOLID_ROOT=${solid}
            export USD_SOLID_OCCT_RUNTIME=${usdSolidOcct.packages.${system}.runtime}
            export AECO_EXACT_CACHE="$PWD/.work/exact-native"
            export AECO_DATACENTRE_ROOT=${datacentre}
            export PXR_PLUGINPATH_NAME=${plugins}
          '';
          example = pkgs.writeShellApplication {
            name = "example";
            runtimeInputs = [ kit.pythonEnv kit.usd-dev pkgs.clang ];
            text = setup + ''
              cp -R ${self} example-work
              chmod -R u+w example-work
              env -u PYTHONPATH python example-work/examples/datacentre/run.py "$@"
            '';
          };
          render = pkgs.writeShellApplication {
            name = "render";
            runtimeInputs = [ kit.pythonEnv kit.usd-dev pkgs.clang ];
            text = setup + ''
              env -u PYTHONPATH usdaeco-render ${self}/usdAecoClash/examples/minimal.usda \
                --cameras ${self}/examples/datacentre/inputs/cameras.usda "$@"
            '';
          };
        in { inherit kit pkgs schema plugins setup example render; };
    in {
      packages = eachSystem (system: let p = forSystem system; in {
        default = p.schema;
        pluginSet = p.plugins;
      });
      checks = eachSystem (system: let p = forSystem system; in {
        library = p.pkgs.runCommand "usdAecoClash-check" {
          nativeBuildInputs = [ p.kit.pythonEnv p.kit.usd-dev p.pkgs.clang ];
        } (p.setup + ''
          cp -R ${self} source
          chmod -R u+w source
          cd source
          env -u PYTHONPATH PYTHONPATH="${core}:$PWD" python check.py
          env -u PYTHONPATH python -m pytest -q
          mkdir -p "$out"
        '');
        structure = p.pkgs.runCommand "usdAecoClash-structure" {
          nativeBuildInputs = [ p.kit.pythonEnv ];
        } (p.setup + ''
          env -u PYTHONPATH usdaeco-check structure ${self}
          mkdir -p "$out"
        '');
      });
      devShells = eachSystem (system: let p = forSystem system; in {
        default = p.pkgs.mkShell {
          packages = [ p.kit.pythonEnv p.kit.usd-dev p.pkgs.clang ];
          shellHook = p.setup + "unset PYTHONPATH";
        };
      });
      apps = eachSystem (system: let p = forSystem system; in {
        example = { type = "app"; program = "${p.example}/bin/example"; };
        render = { type = "app"; program = "${p.render}/bin/render"; };
      });
    };
}
