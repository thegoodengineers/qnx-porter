# libgpiod v2.3.2 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/brgl/libgpiod.git at `v2.3.2` (`3435867dd146`) |
| Build system | meson |
| Toolchain | QNX SDP 8.0, `qnx-cross.ini` in this folder |
| Build | **failed** after 1 round(s) |
| Library's own tests | not run |
| Patches kept | 0 (0 by rule, 0 by model) |
| Time | 0.0 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| - | - | - | - | - | no changes needed |

Note: Linux GPIO character-device API: expected not to port

All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- `src/meson.build:4:0: ERROR: Meson version is 0.61.2 but project requires >= 0.64.0`
