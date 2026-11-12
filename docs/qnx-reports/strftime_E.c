/* strftime/wcsftime with the E and O modifiers; compare QNX 8.0 with glibc (docs/qnx-reports/strftime-E-modifier.md). */
#include <stdio.h>
#include <time.h>
#include <stdlib.h>
#include <wchar.h>
int main(void) {
    const char *specs[] = {"%x", "%X", "%D", "%c", "%r", "%Ex", "%EX", "%Ec", "%Ey", "%EY", "%EC", "%Od", "%OH", "%Oy", "%p", "%a"};
    time_t t = 1762934400; struct tm tm = *gmtime(&t);
    for (unsigned i = 0; i < sizeof specs / sizeof *specs; i++) {
        char b[128]; size_t n = strftime(b, sizeof b, specs[i], &tm);
        wchar_t w[128]; wchar_t ws[8]; mbstowcs(ws, specs[i], 8); size_t m = wcsftime(w, 128, ws, &tm);
        printf("%-4s -> %zu \"%s\"   wcsftime %zu\n", specs[i], n, n ? b : "", m);
    }
    return 0;
}
