#include "textutil.h"
int main(void) { return same_word("QNX", "qnx") && !same_word("QNX", "Linux") ? 0 : 1; }
