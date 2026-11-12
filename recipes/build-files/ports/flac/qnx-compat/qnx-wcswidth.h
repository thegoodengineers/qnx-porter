/* qnx-porter: POSIX wcswidth() on top of QNX 8.0's wcwidth() */
#include <stddef.h>
#include <wchar.h>
static inline int qnx_porter_wcswidth(const wchar_t *s, size_t n)
{
    int width = 0;
    for (; n > 0 && *s != L'\0'; n--, s++) {
        int w = wcwidth(*s);
        if (w < 0)
            return -1;
        width += w;
    }
    return width;
}
#define wcswidth qnx_porter_wcswidth
