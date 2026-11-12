# QNX 8.0: strtod() and atof() are not correctly rounded

**Status:** draft report for QNX, not sent. Found by qnx-porter's campaign (pugixml's own tests), reproduced
with the program below on 12 Nov 2026. The team decides whether and where to send it.

## Summary
On QNX SDP 8.0 (build 141, x86_64, QEMU with KVM), `strtod()` and `atof()` often return a double one to four
units in the last place (ULP) away from the correctly rounded value. `sscanf("%lf")` on the same system
returns the correctly rounded value, and so does glibc's `strtod()` on the same machine. Formatting is not
the problem: `printf("%.17g")` prints the same digits on both systems.

## Reproduce
`strtod_roundtrip.c` (this folder) prints 100,000 random finite doubles with `%.17g` and parses each back:

```
qcc -Vgcc_ntox86_64 -O0 strtod_roundtrip.c -o strtod_roundtrip
```

Output on Linux (glibc, WSL Ubuntu 22.04):
```
100000 random doubles: 0 (0.00%) parse back wrong; worst 0 ulp; 0/1/2/>2 ulp: 100000/0/0/0
strtod("0.1") = 0.10000000000000001 (exact nearest double: 0.10000000000000001)
sscanf %lf = 98.765432101234495, atof = 98.765432101234495
```

Output on the QNX 8.0 x86_64 target:
```
100000 random doubles: 51051 (51.05%) parse back wrong; worst 4 ulp; 0/1/2/>2 ulp: 48949/44406/6238/407
strtod("0.1") = 0.10000000000000001 (exact nearest double: 0.10000000000000001)
sscanf %lf = 98.765432101234495, atof = 98.765432101234509
```

## Why it matters
C17 7.22.1.3 lets an implementation be off by one ULP for decimal strings with more significant digits than
`DECIMAL_DIG`, but `%.17g` output has 17 digits, which is within that bound for IEEE double, so the value must
round-trip. Text formats (JSON, XML, YAML, CSV, configuration files) depend on this: a value written and read
back changes. In our campaign, 7 of pugixml 1.14's 962 tests and 4 of jansson 2.14's 213 tests fail on QNX
for this reason alone (`ports/pugixml/logs/tests.log`, `ports/jansson/logs/tests.log`).

## A second library: jansson 2.14
4 of jansson's 213 tests fail on QNX 8.0 (`valid/real-exponent`, `valid/real-subnormal-number` and their
`__strip` variants). `strtod_inputs.c` (this folder) parses exactly those inputs:

```
--- Linux
123e45                       strtod 1.2299999999999999e+47   sscanf 1.2299999999999999e+47
1.8011670033376514e-308      strtod 1.8011670033376514e-308   sscanf 1.8011670033376514e-308
--- QNX 8.0
123e45                       strtod 1.2300000000000002e+47   sscanf 1.2299999999999999e+47
1.8011670033376514e-308      strtod 1.8011670033376509e-308   sscanf 1.8011670033376514e-308
```
jansson's expected outputs are `1.2299999999999999e47` and `1.8011670033376514e-308`.

## Workaround until fixed
`sscanf(s, "%lf", &d)` returns the correctly rounded value on QNX 8.0.
