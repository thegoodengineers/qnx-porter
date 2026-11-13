/* poll() revents on a pipe's read end after its write end is closed: Linux reports POLLHUP (nng 2.x stops its
 * poller thread on it). Prints the bits QNX reports. */
#include <poll.h>
#include <stdio.h>
#include <unistd.h>
static void show(const char *what, int fd) {
    struct pollfd p = {fd, POLLIN, 0};
    int n = poll(&p, 1, 1000);
    printf("%-34s poll=%d revents=%#x POLLIN=%d POLLHUP=%d\n", what, n, p.revents,
           !!(p.revents & POLLIN), !!(p.revents & POLLHUP));
}
int main(void) {
    int fds[2];
    char c;
    pipe(fds);
    write(fds[1], "x", 1);
    show("byte waiting, writer open:", fds[0]);
    close(fds[1]);
    show("byte waiting, writer closed:", fds[0]);
    printf("read: %zd\n", read(fds[0], &c, 1));
    show("empty, writer closed:", fds[0]);
    printf("read: %zd (0 = end of file)\n", read(fds[0], &c, 1));
    return 0;
}
