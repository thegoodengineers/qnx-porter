#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* How far is strtod(printf("%.17g", x)) from x, in units in the last place, over many doubles? */
static int64_t ulps(double a, double b)
{
    int64_t ia, ib;
    memcpy(&ia, &a, 8);
    memcpy(&ib, &b, 8);
    return ia > ib ? ia - ib : ib - ia;
}

int main(void)
{
    uint64_t x = 88172645463325252ull;
    int n = 100000, off = 0;
    int64_t worst = 0, hist[4] = { 0 };
    for (int i = 0; i < n; i++) {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;          /* xorshift: random bit patterns */
        double v;
        uint64_t bits = (x & 0x7fefffffffffffffull);         /* finite, positive */
        memcpy(&v, &bits, 8);
        char buf[40];
        snprintf(buf, sizeof buf, "%.17g", v);
        int64_t d = ulps(strtod(buf, NULL), v);
        if (d) off++;
        if (d > worst) worst = d;
        hist[d > 2 ? 3 : d]++;
    }
    printf("%d random doubles: %d (%.2f%%) parse back wrong; worst %lld ulp; 0/1/2/>2 ulp: %lld/%lld/%lld/%lld\n",
           n, off, 100.0 * off / n, (long long)worst, (long long)hist[0], (long long)hist[1], (long long)hist[2],
           (long long)hist[3]);
    double a = strtod("0.1", NULL);
    printf("strtod(\"0.1\") = %.17g (exact nearest double: 0.10000000000000001)\n", a);
    double s;
    sscanf("98.7654321012345", "%lf", &s);
    printf("sscanf %%lf = %.17g, atof = %.17g\n", s, atof("98.7654321012345"));
    return 0;
}
