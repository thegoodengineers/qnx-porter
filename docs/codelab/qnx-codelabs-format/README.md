# The codelab in QNX's codelab format

`markdown/port-cmake-library-qnx/port-cmake-library-qnx.md` is
[../port-a-library.md](../port-a-library.md) laid out the way [qnx/codelabs](https://github.com/qnx/codelabs)
keeps its codelabs: one folder per codelab under `markdown/`, and an `id` that matches the folder and file name.
Only `id` and `feedback_link` differ from our copy; `tests/test_codelab.py` checks that the rest stays identical.

Nothing has been sent to qnx/codelabs. If the team decides to propose it, QNX's own codelab
[Create Your Own Codelab](https://qnx.github.io/codelabs/codelab-to-create-codelab/index.html) describes the steps:
fork qnx/codelabs, copy this `markdown/port-cmake-library-qnx/` folder into the fork's `markdown/`, change nothing
outside it, optionally preview it with QNX's `claat` (`claat export -f html -o docs ./markdown/port-cmake-library-qnx/port-cmake-library-qnx.md`),
and open a pull request.
