# libgpiod v2.2.4 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/brgl/libgpiod.git at `v2.2.4` (`328d48b8cc90`) |
| Build system | autotools |
| Toolchain | QNX SDP 8.0, `qnx-env.sh` in this folder |
| Build | **failed** after 1 round(s) |
| Library's own tests | not run |
| Patches kept | 0 (0 by rule, 0 by model) |
| Time | 0.2 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| - | - | - | - | - | no changes needed |

Note: Linux GPIO character-device API: expected not to port

All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- `configure: error: linux/const.h header not found (needed to build the library)`
