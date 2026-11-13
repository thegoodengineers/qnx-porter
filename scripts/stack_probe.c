/* How much stack a QNX process's main thread gets. Recurses with 1 KiB frames and prints the depth every 16 KiB;
 * the last line before the fault is the usable stack.
 *   qcc -Vgcc_ntox86_64 -O0 -o sp_default stack_probe.c         (x86_64 QNX 8.0 target: 464 KiB)
 *   qcc -Vgcc_ntox86_64 -O0 -N8M -o sp_8m stack_probe.c         (7472 KiB)
 *   ./sp_default > d.out; tail -1 d.out
 * crash.deep_recursion() and the main-stack fix in agent.py rest on this measurement. */
#include <stdio.h>
#include <unistd.h>
static int down(int d) {
    volatile char pad[1024];
    pad[0] = (char)d;
    if (d % 16 == 0) { char b[32]; int n = snprintf(b, sizeof b, "%d KiB\n", d); write(1, b, n); }
    return down(d + 1) + pad[0];
}
int main(void) { return down(1); }
