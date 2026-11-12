/* qsort() with a comparator that answers at random (as libsrtp 2.6's test/ut_sim.c does).
   C17 7.22.5p4 requires consistent answers, so this is undefined behaviour; the question is only
   whether the libc stays inside the array. Guard words on both sides detect writes outside it. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#define N 160
#define GUARD 64
static int rnd(const void *a, const void *b) { (void)a; (void)b; return (rand() & 0xff) > 127 ? -1 : 1; }
int main(void) {
    static uint32_t mem[GUARD + N + GUARD];
    uint32_t *buf = mem + GUARD;
    int bad = 0, trials = 2000;
    srand(1);
    for (int t = 0; t < trials; t++) {
        for (int i = 0; i < GUARD; i++) mem[i] = mem[GUARD + N + i] = 0xdeadbeef;
        for (int i = 0; i < N; i++) buf[i] = i;
        qsort(buf, N, sizeof *buf, rnd);
        int out = 0;
        for (int i = 0; i < GUARD; i++) out += (mem[i] != 0xdeadbeef) + (mem[GUARD + N + i] != 0xdeadbeef);
        bad += out != 0;
    }
    printf("%d of %d qsort calls wrote outside the array\n", bad, trials);
    return 0;
}
