#!/pxrpythonsubst
from pathlib import Path
import unittest
import json
from pxr import Plug,Sdf,Usd,UsdValidation

ROOT = Path(__file__).resolve().parents[1]
Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoClashValidators'))


class TestValidators(unittest.TestCase):
    def setUp(self):
        self.stage = Usd.Stage.CreateInMemory()
        self.test = self.stage.DefinePrim('/Test','AecoClashTest')
        self.result = self.stage.DefinePrim('/Test/Result','AecoClashResult')
        for path in ('/A','/B'):
            self.stage.DefinePrim(path,'Xform').ApplyAPI('AecoElementAPI')

    def validate(self, name):
        validator = UsdValidation.ValidationRegistry().GetOrLoadValidatorByName('usdAecoClashValidators:'+name+'Checker')
        self.assertIsNotNone(validator)
        return validator.Validate(self.result)

    def test_ClashResultWithoutElements(self):
        self.assertEqual(self.result.GetRelationship('aeco:clash:elements').GetTargets(),[])
        self.assertEqual([e.GetName() for e in self.validate('ClashResultWithoutElements')],['ClashResultWithoutElements'])
        rel = self.result.CreateRelationship('aeco:clash:elements')
        for targets in (['/A'],['/A','/Missing'],['/A','/B','/Test']):
            rel.SetTargets(targets)
            self.assertEqual(len(self.validate('ClashResultWithoutElements')),1)
        rel.SetTargets(['/A','/B'])
        self.assertEqual(self.validate('ClashResultWithoutElements'),[])

    def test_ClashUncertaintyExceedsTolerance(self):
        prop = self.result.CreateAttribute('aeco:clash:uncertainty',Sdf.ValueTypeNames.Double)
        prop.Set(.006)
        self.assertGreater(prop.Get(),self.test.GetAttribute('aeco:clash:tolerance').Get())
        errors = self.validate('ClashUncertaintyExceedsTolerance')
        self.assertEqual([e.GetName() for e in errors],['ClashUncertaintyExceedsTolerance'])
        self.assertEqual(errors[0].GetType(),UsdValidation.ValidationErrorType.Warn)
        prop.Set(.0002)
        self.assertEqual(self.validate('ClashUncertaintyExceedsTolerance'),[])
        for value in (float('nan'),float('inf'),-.001):
            prop.Set(value)
            self.assertEqual(len(self.validate('ClashUncertaintyExceedsTolerance')),1)

    def test_ClashStatusUnreviewed(self):
        self.assertEqual(self.result.GetAttribute('aeco:clash:status').Get(),'new')
        self.assertEqual([e.GetName() for e in self.validate('ClashStatusUnreviewed')],['ClashStatusUnreviewed'])
        self.result.CreateAttribute('aeco:clash:status',Sdf.ValueTypeNames.Token).Set('reviewed')
        self.assertEqual(self.validate('ClashStatusUnreviewed'),[])

    def test_ClashRouteDisagreement(self):
        other = self.stage.DefinePrim('/Test/ExactResult','AecoClashResult')
        for prim,method,distance,band,kind in ((self.result,'mesh',-.01,.001,'hard'),
                                             (other,'exact',.005,.00002,'clearance')):
            prim.CreateRelationship('aeco:clash:elements').SetTargets(['/B','/A'])
            prim.CreateAttribute('aeco:clash:evidence',Sdf.ValueTypeNames.String).Set(json.dumps({'method':method}))
            prim.CreateAttribute('aeco:clash:distance',Sdf.ValueTypeNames.Double).Set(distance)
            prim.CreateAttribute('aeco:clash:uncertainty',Sdf.ValueTypeNames.Double).Set(band)
            prim.CreateAttribute('aeco:clash:kind',Sdf.ValueTypeNames.Token).Set(kind)
        self.assertGreater(.015,.00102)  # Seeded contradictory disjoint bands.
        validator = UsdValidation.ValidationRegistry().GetOrLoadValidatorByName(
            'usdAecoClashValidators:ClashRouteDisagreementChecker')
        errors = validator.Validate(self.stage)
        self.assertEqual([e.GetName() for e in errors],['ClashRouteDisagreement'])
        self.assertEqual(errors[0].GetType(),UsdValidation.ValidationErrorType.Warn)
        self.assertEqual(len(errors[0].GetSites()),2)
        self.result.GetAttribute('aeco:clash:uncertainty').Set(.02)
        self.assertEqual(validator.Validate(self.stage),[])
        self.result.GetAttribute('aeco:clash:uncertainty').Set(.001)
        other.GetAttribute('aeco:clash:kind').Set('hard')
        self.assertEqual(validator.Validate(self.stage),[])


if __name__ == '__main__':
    unittest.main()
