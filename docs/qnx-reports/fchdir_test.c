/* Does fchdir() return to a directory opened with open(".", O_RDONLY)? googletest's QNX death-test path
   does exactly this around spawn() (gtest-death-test.cc). */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(void) {
    char before[512], after[512];
    getcwd(before, sizeof before);
    int fd = open(".", O_RDONLY);
    printf("open(\".\", O_RDONLY) = %d (%s)\n", fd, fd < 0 ? strerror(errno) : "ok");
    int fd2 = open(".", O_RDONLY | O_DIRECTORY);
    printf("open(\".\", O_RDONLY|O_DIRECTORY) = %d (%s)\n", fd2, fd2 < 0 ? strerror(errno) : "ok");
    if (chdir("/") != 0) perror("chdir /");
    int r = fchdir(fd);
    printf("fchdir(fd) = %d (%s)\n", r, r ? strerror(errno) : "ok");
    if (fd2 >= 0) { chdir("/"); r = fchdir(fd2); printf("fchdir(fd2) = %d (%s)\n", r, r ? strerror(errno) : "ok"); }
    getcwd(after, sizeof after);
    printf("cwd before %s, after %s\n", before, after);
    return 0;
}
