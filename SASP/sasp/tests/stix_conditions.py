from django.test import TestCase, Client
from django.urls import reverse

import sasp.automation_component.stix_parsing as stix_parsing
from pathlib import Path
import json

resource_path = Path(__file__).parent / "resources"

# return {
#     "var_id": self.object.get_cacao_id(),
#     "var_type": self.object.Field_Type.get_field(self.object),
#     "var_value": json.loads(self.object.Field_Value.get_field(self.object)),
#     "var_constant": self.object.Field_Constant.get_field(self.object, default=False),
# }

class TestStix(TestCase):
    context = {
        "$$var_int$$": {
            "var_id": "$$var_int$$",
            "var_type": "integer",
            "var_value": 1,
            "var_constant": False,
        },
        "$$var_str$$": {
            "var_id": "$$var_str$$",
            "var_type": "string",
            "var_value": "string",
            "var_constant": False,
        },
        "$$var_dict$$": {
            "var_id": "$$var_dict$$",
            "var_type": "dictionary",
            "var_value": {"key": ["value1", "value2"]},
            "var_constant": False,
        },
    }
    def test_conditions(self):
        self.assertEqual(stix_parsing.parse_if_condition(
            "[$$var_int$$ = 1]", self.context), True)        
        self.assertEqual(stix_parsing.parse_if_condition(
            "[$$var_dict$$:key[0] = 'value1']", self.context), True)
        self.assertEqual(stix_parsing.parse_if_condition(
            "[$$var_dict$$:key[*] = 'value1']", self.context), True)
        self.assertEqual(stix_parsing.parse_if_condition(
            "[$$var_dict$$:key[*] = 'value1'] AND [$$var_int$$ < 10]", self.context), True)
        self.assertEqual(stix_parsing.parse_if_condition(
            "[$$var_dict$$:key[*] = 'value1'] AND [$$var_int$$ < 10.5]", self.context), True)
        
    
    def test_read_variable(self):
        self.assertEqual(stix_parsing.get_variable_value(
            "$$var_int$$", self.context), [self.context["$$var_int$$"]["var_value"]])
        self.assertEqual(stix_parsing.get_variable_value(
            "$$var_str$$", self.context), [self.context["$$var_str$$"]["var_value"]])
        self.assertEqual(stix_parsing.get_variable_value(
            "$$var_dict$$", self.context), [self.context["$$var_dict$$"]["var_value"]])
        self.assertEqual(stix_parsing.get_variable_value(
            "$$var_dict$$:key[1]", self.context), [self.context["$$var_dict$$"]["var_value"]['key'][1]])
        self.assertEqual(stix_parsing.get_variable_value(
            "$$var_dict$$:key[*]", self.context), self.context["$$var_dict$$"]["var_value"]['key'])
