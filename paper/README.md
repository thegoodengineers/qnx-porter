# The qnx-porter paper

`qnx-porter.tex` is the source. Every number in it is written as `\N{key}`; `build.py` defines each key from the
repository's result files (`results/*.csv`, `ports*/*/report.json`, `results/runs/*.log` and the generated docs)
and fails if the paper uses one it does not define. The figures are drawn from the same CSVs.

| File | Made by |
|---|---|
| `numbers.tex` | `build.py` |
| `paper.md` (the same paper as Markdown, for the website) | `build.py`, from `qnx-porter.tex` |
| `fig/*.pdf`, `fig/*.png` | `figures.py` (needs matplotlib) |
| `qnx-porter.pdf` | Tectonic, from `qnx-porter.tex` |

## Rebuild after a campaign

```bash
python3 -m pip install --user matplotlib    # once, for the figures
python3 paper/figures.py                      # fig/ from the CSVs
python3 paper/build.py && tectonic paper/qnx-porter.tex
```

Tectonic is a single-binary LaTeX engine
([releases](https://github.com/tectonic-typesetting/tectonic/releases), the `x86_64-unknown-linux-musl` tarball);
it downloads the TeX packages it needs on first use. `tests/test_paper.py` checks in CI that every number the
paper uses is defined and that `paper.md` renders.

Prose that names a specific library's failure describes the run whose logs it cites (the 2024 pins). After a new
campaign, re-read Sections 4.1 and 6 for sentences the new numbers no longer support.
