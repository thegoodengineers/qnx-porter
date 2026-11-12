#include <stdio.h>
#include <stdlib.h>

/* The inputs of jansson's failing tests valid/real-exponent and valid/real-subnormal-number. */
int main(int argc, char **argv)
{
    for (int i = 1; i < argc; i++) {
        double d = strtod(argv[i], NULL), s;
        sscanf(argv[i], "%lf", &s);
        printf("%-28s strtod %.17g   sscanf %.17g\n", argv[i], d, s);
    }
    return 0;
}
