"""Schema-scoped Python validators registered through UsdValidation."""
import math
import json
from pxr import UsdValidation
from . import validatorTokens as tokens


def error(prim, name, severity, message):
    return [UsdValidation.ValidationError(name, severity,
        [UsdValidation.ValidationErrorSite(prim.GetStage(),prim.GetPath())],message)]


def elements_task(prim, time_range):
    if prim.GetTypeName() != 'AecoClashResult':
        return []
    targets = prim.GetRelationship('aeco:clash:elements').GetTargets()
    if len(targets) != 2 or len(set(targets)) != 2 or any(
        not prim.GetStage().GetPrimAtPath(p) or not prim.GetStage().GetPrimAtPath(p).HasAPI('AecoElementAPI') for p in targets):
        return error(prim,tokens.WITHOUT_ELEMENTS,UsdValidation.ValidationErrorType.Error,
                     'A clash result requires exactly two distinct existing elements.')
    return []


def uncertainty_task(prim, time_range):
    if prim.GetTypeName() != 'AecoClashResult':
        return []
    value = prim.GetAttribute('aeco:clash:uncertainty').Get()
    tolerance = prim.GetParent().GetAttribute('aeco:clash:tolerance').Get()
    if value is None or tolerance is None or not math.isfinite(value) or value < 0 or not math.isfinite(tolerance) or tolerance < 0 or value > tolerance:
        return error(prim,tokens.UNCERTAINTY_EXCEEDS_TOLERANCE,UsdValidation.ValidationErrorType.Warn,
                     'Body uncertainty exceeds the test tolerance or the uncertainty band is invalid; review the evidence.')
    return []


def status_task(prim, time_range):
    if prim.GetTypeName() != 'AecoClashResult':
        return []
    if prim.GetAttribute('aeco:clash:status').Get() not in ('reviewed','approved','resolved'):
        return error(prim,tokens.STATUS_UNREVIEWED,UsdValidation.ValidationErrorType.Warn,
                     'Clash result has not been reviewed.')
    return []


def disagreement_task(stage, time_range):
    groups = {}
    for prim in stage.Traverse():
        if prim.GetTypeName() != 'AecoClashResult':
            continue
        try:
            method = json.loads(prim.GetAttribute('aeco:clash:evidence').Get())['method']
        except (TypeError, ValueError, KeyError):
            continue
        if method not in ('mesh', 'exact'):
            continue
        targets = tuple(sorted(prim.GetRelationship('aeco:clash:elements').GetTargets()))
        if len(targets) != 2:
            continue
        key = (prim.GetParent().GetPath(), targets)
        groups.setdefault(key, {}).setdefault(method, []).append(prim)
    errors = []
    for routes in groups.values():
        for mesh in routes.get('mesh', []):
            for exact in routes.get('exact', []):
                values = [p.GetAttribute('aeco:clash:'+field).Get()
                          for p in (mesh, exact) for field in ('distance','uncertainty')]
                if any(v is None or not math.isfinite(v) for v in values) or min(values[1],values[3]) < 0:
                    continue
                # Hard distances measure different things (sampled interior
                # depth versus zero separation). Compare differing verdicts
                # only; a sign/category difference inside either band is normal.
                if (mesh.GetAttribute('aeco:clash:kind').Get() != exact.GetAttribute('aeco:clash:kind').Get()
                        and abs(values[0]-values[2]) > values[1]+values[3]):
                    errors.append(UsdValidation.ValidationError(tokens.ROUTE_DISAGREEMENT,
                        UsdValidation.ValidationErrorType.Warn,
                        [UsdValidation.ValidationErrorSite(stage, p.GetPath()) for p in (mesh, exact)],
                        'Mesh and exact verdicts differ beyond their combined uncertainty bands.'))
    return errors


_registry = UsdValidation.ValidationRegistry()
_registry.RegisterPluginPrimValidator(tokens.ELEMENTS_CHECKER,elements_task)
_registry.RegisterPluginPrimValidator(tokens.UNCERTAINTY_CHECKER,uncertainty_task)
_registry.RegisterPluginPrimValidator(tokens.STATUS_CHECKER,status_task)
_registry.RegisterPluginStageValidator(tokens.ROUTE_CHECKER,disagreement_task)
