import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from measure_native_budget import (PWV4_BYTES, SAMPLE, analyze, divide_iterations,
                                   measure, sections)


class BudgetHelpers(unittest.TestCase):
    def test_divide_iterations_matches_the_native_loop(self):
        # shift is zero whenever the quotient is 0 or 1, so one pass runs.
        self.assertEqual(divide_iterations(0, 1), 1)
        self.assertEqual(divide_iterations(1, 1), 1)
        self.assertEqual(divide_iterations(2, 1), 3)
        self.assertEqual(divide_iterations(255 * 255, 1), 31)
        with self.assertRaises(ValueError):
            divide_iterations(1, 0)
        # The count is exactly floor(log2(n/d)) shifts plus the same number back.
        for denominator in (1, 3, 31, 255):
            for numerator in (0, 1, denominator, denominator * 27 + 7, 65025):
                quotient = numerator // denominator
                shifts = max(quotient.bit_length() - 1, 0)
                self.assertEqual(divide_iterations(numerator, denominator), 2 * shifts + 1)

    def test_sections_refuses_malformed_envelopes(self):
        with self.assertRaises(ValueError):
            list(sections(b'NOPE' + bytes(16)))
        with self.assertRaises(ValueError):
            list(sections(b'PMAI'))
        # Section header below the 12-byte minimum is refused, not skipped.
        broken = b'PMAI' + struct.pack('>II', 12, 28) + b'PWV4' + struct.pack('>II', 4, 16)
        with self.assertRaises(ValueError):
            list(sections(broken + bytes(8)))

    def test_measure_requires_the_exact_payload_length(self):
        for length in (0, PWV4_BYTES - 1, PWV4_BYTES + 1):
            with self.assertRaises(ValueError):
                measure(bytes(length))

    def test_silence_still_produces_one_division_per_layer_height(self):
        counts = measure(bytes(PWV4_BYTES))
        # Both colour layers are skipped when the magnitude is zero; the interval
        # boundary and the two height divisions per column remain.
        self.assertEqual(counts['divisions'], 3 * 80)
        self.assertEqual(counts['inner_compares'], 80 * 14 * 4)
        self.assertEqual(counts['global_max_records'], 1200)

    def test_full_intensity_uses_every_colour_division(self):
        counts = measure(b'\x00\x00\x00\xff\xff\xff' * 1200)
        # One interval boundary, two heights and six colour channels per column.
        self.assertEqual(counts['divisions'], 9 * 80)


@unittest.skipUnless((SAMPLE / 'color-manifest.json').exists(),
                     'Private owner colour sample absent')
class BudgetOnOwnerExport(unittest.TestCase):
    def test_counts_are_bounded_and_reported(self):
        report = analyze()
        self.assertEqual(report['files_measured'], 50)
        average = report['per_cell_average']
        # Nine divisions per column is the ceiling; silence lowers it.
        self.assertLessEqual(average['divisions'], 9 * 80)
        self.assertGreater(average['divisions'], 0)
        # Iterations are 2*floor(log2(quotient)) + 1. The interval boundary
        # reaches 1200 (21 passes), heights reach 27 (9) and colour channels
        # reach the layer intensity 255 (15).
        self.assertLessEqual(average['divide_iterations'], 80 * (21 + 2 * 9 + 6 * 15))
        self.assertEqual(report['per_cell_draw']['stores'], 2240)
        self.assertEqual(report['memory_bytes']['destination_per_row'], 4480)
