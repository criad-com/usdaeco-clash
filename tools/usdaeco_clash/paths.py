"""Study paths and relocation of library-owned layers, without editing sources."""
import os
from pathlib import Path
from pxr import Sdf

ROOT_KEY = 'aeco:clash:studyRoot'


def study_root(stage=None, test_path=None):
    """Persisted metadata/test locations take precedence over the environment."""
    value = None
    if test_path is not None:
        parent = Sdf.Path(test_path).GetParentPath()
        if parent.name == 'Clash':
            value = str(parent.GetParentPath())
    if stage is not None and value is None:
        value = stage.GetRootLayer().customLayerData.get(ROOT_KEY)
        if value is None:
            roots = {p.GetPath().GetParentPath().GetParentPath()
                     for p in stage.Traverse() if p.GetTypeName() == 'AecoClashTest'
                     and p.GetParent().GetName() == 'Clash'}
            if len(roots) == 1:
                value = str(roots.pop())
    value = value if value is not None else os.environ.get('AECO_STUDY_ROOT', '/')
    path = Sdf.Path(value)
    if not path.IsAbsolutePath() or not (path.IsPrimPath() or path == Sdf.Path.absoluteRootPath) or path.ContainsPrimVariantSelection():
        raise ValueError('AECO_STUDY_ROOT must be an absolute prim path or /')
    return path


def resolve_test(stage, selection=None):
    """Find a test by absolute path or unique name; omit for a single-test stage."""
    tests = [p for p in stage.Traverse() if p.GetTypeName() == 'AecoClashTest']
    if selection is not None:
        tests = [p for p in tests if str(p.GetPath()) == str(selection) or p.GetName() == str(selection)]
    if len(tests) != 1:
        raise ValueError('Select one AecoClashTest with --test (absolute path or unique name)')
    return tests[0].GetPath()


def scope(layer, path):
    """Define plain Scope ancestors for a library's external records."""
    for prefix in Sdf.Path(path).GetPrefixes():
        prim = Sdf.CreatePrimInLayer(layer, prefix)
        prim.specifier = Sdf.SpecifierDef
        prim.typeName = 'Scope'


def camera_path(name, root):
    return Sdf.Path('/Renders').AppendPath('clash/' + name) if root != Sdf.Path.absoluteRootPath else Sdf.Path('/Renders').AppendChild(name)


def scope_layer(layer, root):
    """Rebase a writable clash layer, including bindings, connections and paths.

    Also accepts copies of the committed exact/twin/result layers. The source
    project and its catalog remain in place. The default is a byte-preserving no-op.
    """
    root = Sdf.Path(root)
    if root == Sdf.Path.absoluteRootPath:
        return
    moves = []
    mappings = []
    for name in ('Clash', 'ExactMaterials', '__ExactPrototypes'):
        old = Sdf.Path.absoluteRootPath.AppendChild(name)
        mappings.append((old, root.AppendChild(name)))
        if layer.GetPrimAtPath(old):
            moves.append((old, root.AppendChild(name)))
    # Cameras from both the inputs and historical result layers belong to Renders.
    paths = []
    layer.Traverse(Sdf.Path.absoluteRootPath, paths.append)
    for path in paths:
        prim = layer.GetPrimAtPath(path)
        if prim and prim.typeName == 'Camera' and not path.HasPrefix(Sdf.Path('/Renders/clash')):
            name = path.GetParentPath().name if path.name == 'Camera' else path.name
            moves.append((path, camera_path(name, root)))
            mappings.append(moves[-1])
    # Copy from a snapshot: moving a parent must not erase a camera before its copy.
    original = Sdf.Layer.CreateAnonymous()
    original.TransferContent(layer)
    for old, _ in sorted(moves, key=lambda pair: len(str(pair[0])), reverse=True):
        edit = Sdf.BatchNamespaceEdit()
        edit.Add(old, Sdf.Path.emptyPath)
        if not layer.Apply(edit):
            raise ValueError('Cannot relocate clash prim: ' + str(old))
    for old, new in moves:
        scope(layer, new.GetParentPath())
        Sdf.CopySpec(original, old, layer, new)
    # A moved Clash copy still contains the old nested result cameras.
    for old, _ in moves:
        if original.GetPrimAtPath(old).typeName == 'Camera':
            for parent, target in moves:
                if old != parent and old.HasPrefix(parent):
                    edit = Sdf.BatchNamespaceEdit()
                    edit.Add(old.ReplacePrefix(parent, target), Sdf.Path.emptyPath)
                    if not layer.Apply(edit):
                        raise ValueError('Cannot remove relocated result camera')
    mappings.sort(key=lambda pair: len(str(pair[0])), reverse=True)

    def mapped(path):
        for old, new in mappings:
            if path.HasPrefix(old):
                return path.ReplacePrefix(old, new)
        return path

    def metadata(value):
        if isinstance(value, dict):
            return {k: metadata(v) for k, v in value.items()}
        if isinstance(value, Sdf.Path):
            return mapped(value)
        if isinstance(value, str) and value.startswith('/') and Sdf.Path.IsValidPathString(value):
            return str(mapped(Sdf.Path(value)))
        return value

    paths = []
    layer.Traverse(Sdf.Path.absoluteRootPath, paths.append)
    for path in paths:
        spec = layer.GetObjectAtPath(path)
        if spec is None:
            continue
        for field, editor in (('targetPaths', 'targetPathList'), ('connectionPaths', 'connectionPathList'),
                              ('inheritPaths', 'inheritPathList'), ('specializes', 'specializesList'),
                              ('references', 'referenceList')):
            if not spec.HasInfo(field):
                continue
            operation = spec.GetInfo(field)
            def item(value):
                if isinstance(value, Sdf.Reference):
                    return Sdf.Reference(value.assetPath, mapped(value.primPath) if not value.assetPath else value.primPath,
                                         value.layerOffset, value.customData)
                return mapped(value)
            for name in (('explicitItems',) if operation.isExplicit else
                         ('addedItems', 'prependedItems', 'appendedItems', 'deletedItems', 'orderedItems')):
                setattr(getattr(spec, editor), name, [item(v) for v in getattr(operation, name)])
        if spec.HasInfo('customData'):
            spec.SetInfo('customData', metadata(spec.GetInfo('customData')))
    layer.customLayerData = {**metadata(layer.customLayerData), ROOT_KEY: str(root)}
    for name in ('ExactMaterials', '__ExactPrototypes'):
        if layer.GetPrimAtPath(root.AppendChild(name)):
            scope(layer, root.AppendChild(name))


def prepare_inputs(stage, out_dir):
    """Copy/rebase the standalone input layers when the suite requests a root."""
    root = study_root()
    if root == Sdf.Path.absoluteRootPath:
        return
    layer = stage.GetRootLayer()
    for index, asset in enumerate(list(layer.subLayerPaths)):
        source = Sdf.Layer.FindOrOpenRelativeToLayer(layer, asset)
        if not source or not source.rootPrims or any(p.name not in ('Clash', 'Renders') for p in source.rootPrims):
            continue
        output = Path(out_dir) / ('scoped-' + Path(source.identifier).name)
        copied = Sdf.Layer.CreateNew(str(output))
        copied.TransferContent(source)
        scope_layer(copied, root)
        copied.Save()
        layer.subLayerPaths[index] = str(output.resolve())
    layer.customLayerData = {**layer.customLayerData, ROOT_KEY: str(root)}
