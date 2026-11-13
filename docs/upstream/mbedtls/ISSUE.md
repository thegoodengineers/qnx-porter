# Draft issue for Mbed-TLS/mbedtls (not sent)

**Status:** draft. Found by qnx-porter's campaign at the latest upstream releases on 13 Nov 2026. The team
decides whether to file it. It is a build-system issue on every OS, not a QNX one.

## Title
CMake: `-DENABLE_PROGRAMS=OFF` with testing enabled fails at configure in 4.2.0 (`add_dependencies` with an
empty target)

## Body
With mbedtls `v4.2.0`, configuring with `-DENABLE_PROGRAMS=OFF` while tests are enabled (the default) stops
at configure:

```
CMake Error at tests/CMakeLists.txt:69 (add_dependencies):
  add_dependencies called with incorrect number of arguments

CMake Error at tests/CMakeLists.txt:85 (add_dependencies):
  add_dependencies called with incorrect number of arguments
```

`tests/CMakeLists.txt` calls `add_dependencies(${ssl_opt_target} ...)`, but the top-level `CMakeLists.txt`
sets `ssl_opt_target` only inside `if(ENABLE_PROGRAMS)` (around line 485, just before
`add_subdirectory(programs)`). With programs off, the variable is empty, and `add_dependencies` gets one
argument.

Two possible fixes: define `ssl_opt_target` (and its custom target) outside the `ENABLE_PROGRAMS` block, or guard the two
`add_dependencies` calls in `tests/CMakeLists.txt` with `if(TARGET ${ssl_opt_target})` / `if(ENABLE_PROGRAMS)`.

Workaround: leave `ENABLE_PROGRAMS` on.

## How it was seen
qnx-porter's `campaign.yaml` used `-DENABLE_PROGRAMS=OFF` for mbedtls 3.6.2, which configured fine. At
`v4.2.0` the same option fails as above, before any compiler runs. With the option removed, the QNX 8.0 build
succeeds after one rule (`link-libsocket`, for `__inet_pton`).
