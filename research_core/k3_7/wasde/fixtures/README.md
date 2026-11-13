These small fixtures are authored schema examples, dedicated to the public
domain under CC0-1.0. **Every numeric value is artificial. They are not USDA
observations, not downloaded raw releases, and not evidence of historical
coverage, official format compatibility, or availability.**

`schema_example.csv` exercises the K3.4 CSV column/unit convention. The release
date is a test identifier; its presence is not a claim of observed publication.
Tests derive other dates, marketing years, revisions and invalid cases in memory.
`archive_example.html` is an authored HTML link-discovery example. Its two
official link targets were seen on the USDA archive through a separate web
lookup; the fixture HTML itself is not a copy of that page.

No fixture is consumed by the online command or written to `out/`. Offline tests
inject in-memory loaders; timestamps and source URLs in those loaders are test
parameters. ZIP fixtures are built in memory with fixed metadata.

An actual official raw fixture/spot-check remains pending because this session's
execution-network policy blocked USDA downloads. Do not describe passing these
tests as online validation. See `SOURCE_FEASIBILITY.md`.
