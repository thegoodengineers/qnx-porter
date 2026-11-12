from qnx_porter import rt

LIB = """#include <stdlib.h>
/* malloc( in a comment is not a call */
static const char *s = "free(this string)";
int parse(struct ctx *c, const char *buf)
{
    char *copy = malloc(16);          /* heap */
    c->read(c, buf);                  /* a member call, not read(2) */
    int n = read(c->fd, copy, 16);    /* blocking I/O */
    usleep(10);
    pthread_mutex_lock(&c->lock);
    free(copy);
    return n;
}
"""


def test_scan_counts_real_calls_only(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "parse.c").write_text(LIB)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.c").write_text("int main(void){ fork(); system(\"x\"); return 0; }\n")
    r = rt.scan(tmp_path)
    h = r["hazards"]
    assert (h["heap"]["count"], h["blocking_io"]["count"], h["sleep"]["count"], h["mutexes"]["count"]) == (2, 1, 1, 1)
    assert h["process"]["count"] == 0  # tests are not the library
    assert h["heap"]["examples"][0] == "src/parse.c:6" and h["blocking_io"]["examples"] == ["src/parse.c:8"]
    assert r["files"] == 1
    assert r["static_score"] == 100 - 20 - 20 - 10 - 10


def test_clean_library_scores_100(tmp_path):
    (tmp_path / "m.c").write_text("int add(int a, int b) { return a + b; }\n")
    assert rt.scan(tmp_path)["static_score"] == 100
