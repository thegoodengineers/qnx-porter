/* A tiny library written on Linux: it relies on headers glibc includes implicitly. */
#include <stddef.h>
#include "textutil.h"

int same_word(const char *a, const char *b)
{
    int unused_on_purpose;
    return strcasecmp(a, b) == 0;
}
