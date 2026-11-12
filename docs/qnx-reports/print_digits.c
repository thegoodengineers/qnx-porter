/* Prints one double three ways; compare QNX 8.0 with glibc (docs/qnx-reports/strtod-rounding.md). */
#include <stdio.h>
#include <stdlib.h>
int main(void) {
    const double x = 0.123456789;
    char b[64];
    snprintf(b, sizeof b, "%.17g", x);
    printf("%%.17g -> %s (round-trips via strtod: %d)\n", b, strtod(b, NULL) == x);
    printf("%%.20f -> %.20f\n", x);
    printf("%%a    -> %a\n", x);
    return 0;
}
