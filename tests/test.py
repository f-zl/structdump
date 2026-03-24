import unittest
import structdump
from pathlib import Path


class TestToJson(unittest.TestCase):
    def test_example(self):
        td = structdump.get_type_dict(
            Path(__file__) / "../../example/a.out", "g_s", "a.c"
        )
        s = td.typedict.to_json()
        self.assertEqual(
            s,
            '{"uint8_t":{"kind":"base","name":"uint8_t","size":1,"encoding":"unsigned_integral"},"uint16_t":{"kind":"base","name":"uint16_t","size":2,"encoding":"unsigned_integral"},"float":{"kind":"base","name":"float","size":4,"encoding":"floating_point"},"int8_t":{"kind":"base","name":"int8_t","size":1,"encoding":"signed_integral"},"uint32_t":{"kind":"base","name":"uint32_t","size":4,"encoding":"unsigned_integral"},"SS":{"kind":"struct","name":"SS","size":8,"members":[{"type":"int8_t","name":"i8","offset":0,"size":1},{"type":"uint32_t","name":"u32","offset":4,"size":4}]},"unsigned int":{"kind":"base","name":"unsigned int","size":4,"encoding":"unsigned_integral"},"Enum":{"kind":"enum","name":"Enum","size":4,"underlying_type":"unsigned int","enumerators":{"E1":0,"E2":1}},"int16_t":{"kind":"base","name":"int16_t","size":2,"encoding":"signed_integral"},"int32_t":{"kind":"base","name":"int32_t","size":4,"encoding":"signed_integral"},"S":{"kind":"struct","name":"S","size":48,"members":[{"type":"uint8_t","name":"u8","offset":0,"size":1},{"type":"uint16_t","name":"u16","offset":2,"size":2},{"type":"float","name":"f32","offset":4,"size":4},{"type":"SS[2]","name":"ss2","offset":8,"size":16},{"type":"Enum","name":"e","offset":24,"size":4},{"type":"SS","name":"ss","offset":28,"size":8},{"type":"int16_t[3]","name":"i16","offset":36,"size":6},{"type":"int32_t","name":"i32","offset":44,"size":4}]}}',
        )
        td2 = td.typedict.from_json(s)
        self.assertEqual(td2, td.typedict)

    def test_find_without_suffix(self):
        _td = structdump.get_type_dict(Path(__file__) / "../../example/a.out", "g_s")
        # pass if no exception is raised


if __name__ == "__main__":
    unittest.main()
