import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from index_next_layout import analyze
STOCK=ROOT/'private/extracted/v144/main-040000-unpacked.bin'

@unittest.skipUnless(STOCK.exists(),'Private stock firmware absent')
class NextLayout(unittest.TestCase):
    def test_all_stock_cache_entries_fit_packed_160_and_refuse_wrong_hash(self):
        data=STOCK.read_bytes();report=analyze(data)
        p=report['plans'][-1]
        self.assertEqual(p['combined_bytes'],25200)
        self.assertEqual(p['source_B_unused_bytes'],1008)
        self.assertEqual(p['destination_B_unused_bytes'],2146)
        self.assertEqual(p['cache_entries_checked'],512)
        self.assertGreaterEqual(p['minimum_end_margin_in_any_cache_entry_bytes'],1008)
        changed=bytearray(data);changed[0x1412724]^=1
        with self.assertRaises(ValueError):analyze(changed)
