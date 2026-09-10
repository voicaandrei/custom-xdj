/* Verifies the shift-and-subtract division used instead of a divide instruction.
 * Includes the translation unit so the internal helper can be checked directly;
 * the reference is the C operator, computed here on the host only. */
#include "waveform_prepare.c"

#include <assert.h>

int main(void)
{
    unsigned int denominator, numerator, level;

    assert(divide(0, 1) == 0);
    assert(divide(0, 255) == 0);
    assert(divide(1, 1) == 1);
    assert(divide(0xffffffffu, 1) == 0xffffffffu);
    assert(divide(0x7fffffffu, 3) == 0x7fffffffu / 3u);

    /* Every divisor the preparation can produce, over every reachable numerator. */
    for (denominator = 1; denominator < 256; ++denominator) {
        /* pixels(): value is never above the running maximum. */
        for (numerator = 0; numerator <= denominator; ++numerator) {
            unsigned int scaled = numerator * XDJ_CELL_AMPLITUDE_HEIGHT
                                  + (denominator >> 1);
            assert(divide(scaled, denominator) == scaled / denominator);
        }
        /* color(): each channel is scaled by the layer intensity. */
        for (level = 0; level < 256; ++level) {
            for (numerator = 0; numerator <= denominator; ++numerator) {
                unsigned int scaled = numerator * level;
                assert(divide(scaled, denominator) == scaled / denominator);
            }
        }
    }

    /* Powers of two and their neighbours, where a shifted divisor could overrun. */
    for (denominator = 1; denominator; denominator <<= 1) {
        unsigned int probes[5];
        unsigned int index;
        probes[0] = denominator - 1u;
        probes[1] = denominator;
        probes[2] = denominator + 1u;
        probes[3] = 0x7fffffffu;
        probes[4] = 0xfffffffeu;
        for (index = 0; index < 5; ++index)
            assert(divide(probes[index], denominator) == probes[index] / denominator);
    }
    return 0;
}
