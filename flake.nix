{
  description = "usdAecoClash semantic library and example";
  inputs = {
    toolchain.url = "github:criad-com/usdaeco-toolchain?ref=v0.3.10";
    nixpkgs.follows = "toolchain/nixpkgs";
    core.url = "github:criad-com/usdaeco-core?ref=v0.9.5";
    core.inputs.toolchain.follows = "toolchain";
    core.inputs.nixpkgs.follows = "nixpkgs";
    core.inputs.datacentre.follows = "datacentre";
    axis.url = "github:criad-com/usdaeco-axis?ref=v0.1.5";
    axis.inputs.core.follows = "core";
    axis.inputs.toolchain.follows = "toolchain";
    axis.inputs.nixpkgs.follows = "nixpkgs";
    axis.inputs.datacentre.follows = "datacentre";
    datacentre.url = "github:criad-com/usdaeco-datacentre?ref=v0.4.8";
    datacentre.flake = false;
    solid.url = "github:criad-com/usdaeco-solid?ref=v0.1.5";
    solid.flake = false;
    ifc.url = "github:criad-com/usdaeco-ifc?ref=v0.2.2";
    ifc.flake = false;
    usdSolid.url = "github:criad-com/usdSolid?ref=v0.1.5";
    usdSolid.inputs.aeco-toolchain.follows = "toolchain/aeco-toolchain";
    usdSolid.inputs.usdaeco-toolchain.follows = "toolchain";
    usdSolidOcct.url = "github:criad-com/usdSolidOcct?ref=v0.1.4";
    usdSolidOcct.flake = false;
  };
  outputs = { self, nixpkgs, toolchain, core, axis, datacentre, solid, ifc, usdSolid, usdSolidOcct }:
    let
      # Build the bridge source using the selected schema and its upstream pins.
      bridgeOutputs = (import (usdSolidOcct + "/flake.nix")).outputs {
        self = usdSolidOcct;
        inherit nixpkgs usdSolid;
        aeco-toolchain = usdSolid.inputs.aeco-toolchain;
        usdaeco-toolchain = toolchain;
        upstream-schema = usdSolid.inputs.upstream;
        upstream-validators = usdSolid.inputs.upstream-validators;
        upstream = usdSolid.inputs.upstream-fixtures;
      };
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
            export USD_SOLID_OCCT_RUNTIME=${bridgeOutputs.packages.${system}.runtime}
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
