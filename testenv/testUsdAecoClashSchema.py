#!/pxrpythonsubst
from pathlib import Path
import unittest
from pxr import Plug, Usd

ROOT = Path(__file__).resolve().parents[1]
Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoClash'))


class TestSchema(unittest.TestCase):
    def test_types_and_collections(self):
        registry = Usd.SchemaRegistry()
        for name in ('AecoClashTest','AecoClashResult'):
            self.assertIsNotNone(registry.FindConcretePrimDefinition(name))
        definition = registry.FindConcretePrimDefinition('AecoClashTest')
        for name in ('members','setA','setB'):
            self.assertIn('CollectionAPI:'+name,definition.GetAppliedAPISchemas())
        self.assertEqual(definition.GetAttributeFallbackValue('aeco:clash:tolerance'),.001)

    def test_derived_contract(self):
        definition = Usd.SchemaRegistry().FindConcretePrimDefinition('AecoClashResult')
        for prop in ('elements','kind','distance','volume','point','uncertainty','evidence'):
            self.assertIs(definition.GetPropertyMetadata('aeco:clash:'+prop,'aecoDerived'),True)
        self.assertIsNot(definition.GetPropertyMetadata('aeco:clash:status','aecoDerived'),True)


if __name__ == '__main__':
    unittest.main()
