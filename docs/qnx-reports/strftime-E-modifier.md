# QNX 8.0: strftime() writes nothing for %Ex, %EX and %Ec

**Status:** draft report for QNX, not sent. Found by qnx-porter's campaign (fmt 11.0.2's own tests), reproduced
with `strftime_E.c` (this folder) on 12 Nov 2026. The team decides whether and where to send it.

## Summary
On QNX SDP 8.0 (build 141, x86_64), `strftime()` and `wcsftime()` return 0 and write an empty string for the
conversions `%Ex`, `%EX` and `%Ec` in the default "C" locale. The other `E` and `O` forms (`%Ey`, `%EY`,
`%EC`, `%Od`, `%OH`, `%Oy`) work.

POSIX (`strftime`, modified conversion specifiers) requires that when the current locale has no alternative
format, a modified conversion behaves as the unmodified one. QNX's own
[`strftime()` page](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/s/strftime.html)
for 8.0 lists `%Ec`, `%Ex` and `%EX` and says the same, so the behaviour also differs from QNX's documentation.
So in the "C" locale `%Ex` must print what `%x` prints, `%EX` what `%X` prints, `%Ec` what `%c` prints.

## Reproduce
```
qcc -Vgcc_ntox86_64 strftime_E.c -o strftime_E
```

On the QNX 8.0 x86_64 target (the lines that differ from Linux):
```
%x   -> 8 "11/12/25"   wcsftime 8
%Ex  -> 0 ""   wcsftime 0
%EX  -> 0 ""   wcsftime 0
%Ec  -> 0 ""   wcsftime 0
```

On Linux (glibc, WSL Ubuntu 22.04):
```
%x   -> 8 "11/12/25"   wcsftime 8
%Ex  -> 8 "11/12/25"   wcsftime 8
%EX  -> 8 "08:00:00"   wcsftime 8
%Ec  -> 24 "Wed Nov 12 08:00:00 2025"   wcsftime 24
```

## Effect seen
fmt 11.0.2 compares its own chrono formatting with the C library's for every conversion. On QNX 8.0,
`chrono-test` and `xchar-test` fail only on `%Ex`, `%EX` and `%Ec` (6 + 6 assertions), because the C++
`std::time_put` facet calls the C library and gets an empty string (`ports-2024/fmt/logs/tests.log`).

## Workaround until fixed
Use `%x`, `%X` and `%c` directly; in the "C" locale they are what the `E` forms must produce.

## Not a bug: `%a` with a different leading digit
fmt's third failing test, `printf-test`, compares `printf("%.3a", 1234.5678)` with fmt's own output: QNX prints
`0x9.a52p+7`, glibc and fmt print `0x1.34ap+10`. C17 7.21.6.1 leaves the leading hexadecimal digit of `%a`
unspecified apart from being nonzero for normal numbers, so both are correct; the test assumes glibc's choice.
