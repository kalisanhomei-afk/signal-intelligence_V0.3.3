# SIGNAL R1f: Free-first research and subscription cost decision (2026-11-22)

Status: PUBLIC_SOURCE_AND_PRICE_REVIEW / NO_SUBSCRIPTION / GATE0_BLOCKED. Existing PR #29 only.

## Decision
Use official primary-source macro series (Fed, Treasury TIC, Treasury bill rates, BIS) first. A publicly downloadable Dartmouth Kenneth French Mkt-RF and RF series is a candidate for an *exploratory statistical proxy*, not an actual SPY/BIL executable return. Verify the academic data's rights (including CRSP/ICE inputs) before automated or commercial use. This changes sequencing, NOT R0 Gate 0 or M0/M1/M2 validation requirements.

Do not buy historical ETF market data to finish the dashboard or the hypothesis registry. A licensed source of actual next-tradable-session prices, cash dividends, splits and full historical coverage is needed only when formal tradable-return testing is justified. The Economist digital subscription is for editorial research, not a financial time-series data license.

## Public evidence and restrictions
- US Treasury daily bill rates CSV: https://home.treasury.gov/interest-rates-data-csv-archive/ ; XML feed: https://home.treasury.gov/treasury-daily-interest-rate-xml-feed
- Fed statistical source: https://www.federalreserve.gov/datadownload/ ; DDP preformatted downloads scheduled to end 2027-03-31; DDP page to disappear 2027-07-01; source release XML remains available. Do not build new dependencies on the retiring DDP service.
- Treasury TIC: https://home.treasury.gov/archives-of-tic-monthly-data-releases ; prior one-cell TIC PASS and post-release ZIP timestamp quarantines remain as recorded in R1c.
- French dataset: https://mba.tuck.dartmouth.edu/pages/faculty/Ken.french/data_library.html ; factors defined at https://mba.tuck.dartmouth.edu/pages/faculty/Ken.French/Data_Library/f-f_5_factors_2x3.html ; public download does not prove broad commercial machine-learning rights. French market portfolio is CRSP shares minus one-month Treasury bill rate, not SPY/BIL executed total return. Historical series revised.
- FRED terms: https://fred.stlouisfed.org/legal/ ; even copyright-labelled public-domain/citation-requested series do not override the FRED Services/API prohibition on use in development/training of software or ML; direct issuers are preferred when their rights permit.

## Supplier and infrastructure price scenarios in USD (public advertised rates, not actual user bills)
| Path | New vendor cash price | Conditions |
|---|---|---|
| Public macro + rights-cleared exploratory proxy | $0 per month / $0 per year | No claim of tradable alpha or full PIT |
| Tiingo Power Commercial | $50 per month or $499 per year | Internal non-generative models only under applicable terms; raw data and backups must be deleted on cancellation absent written exception; SPY/BIL 2007+ coverage, snapshots and audit retention still unverified |
| Twelve Data Business Venture | from $149 per month or $124 per month billed annually ($1,488/year) | Higher price; verify concrete history, corporate actions, retention and license |
| EODHD Commercial Internal | $399 per month or $3,990 per year | Verify same source-level requirements; not historical immutable PIT by default |
| Other commercial/enterprise sources | Request quote | No paid agreement authorized |

Price URLs: https://www.tiingo.com/about/pricing ; https://www.tiingo.com/tos/ ; https://twelvedata.com/pricing-business ; https://eodhd.com/commercial-pricing

Possible low-volume infrastructure, only while usage remains within the applicable free tiers: Cloudflare Pages ($0, 500 builds/month), Workers and D1 ($0 within quotas), Cloudflare R2 ($0 up to 10GB-month and free operation limits), private GitHub Actions (Free plan includes $12 shared monthly compute, Linux 2-core is $0.006/min; user's actual plan and balance not checked). Workers Paid is $5/month minimum if required; optional Supabase Pro starts $25/month. Do not buy both D1 and Supabase by default.

Costs: public research $0/year in *new subscriptions*; Tiingo annual + free infrastructure $499/year, or + Workers Paid $559/year; 12 months Tiingo at monthly billing costs $600, or $660 with Workers Paid; EODHD annual + free infrastructure $3,990/year. Taxes, FX, existing ChatGPT/Economist, AI token fees and staff time excluded. Illustrative operational human review burden is 2–4 hours/month plus 4–8 hours/quarter, not a validated vendor charge. Source URLs: https://docs.github.com/en/billing/concepts/product-billing/github-actions ; https://developers.cloudflare.com/pages/platform/limits/ ; https://developers.cloudflare.com/d1/platform/pricing/ ; https://developers.cloudflare.com/r2/pricing/ ; https://supabase.com/pricing

## When to subscribe
1. During architecture, synthetic tests, public-source metadata and rights verification: $0 new market-data fees.
2. During rights-cleared public-data exploratory research: $0; stop the funding path if no credible incremental predictive value.
3. Only after a vendor confirms SPY/BIL history, actual market OHLC and corporate actions, internal usage, PIT assumptions, audit retention, and code adapters pass synthetic tests: request approval for a **single monthly** commercial subscription trial, not an annual commitment.
4. If ongoing usage is justified, Tiingo annual billing becomes nominally cheaper around ten months of continuous use. Cancellation requires compliance with raw data deletion; no buy-one-month-and-retain data workaround.

No vendor accounts, API captures, backtests, real trades, subscription purchases, merges or deployments occurred in this review. Existing R0–R1e evidence remains frozen and Gate 0 stays BLOCKED. Next best work is read-only rights and schema validation for the French factor proxy; formal R2 remains blocked.

## Owner-approved supplier-selection policy (2026-11-22)
**OWNER DECISION — APPROVED:** retain the free-first sequence. Do not select Tiingo solely because it is the lowest advertised-price commercial candidate. Tiingo, Twelve Data, EODHD and possibly broker/native sources are *comparative candidates*, not preselected suppliers. No paid subscriptions until separately authorized.

**Mandatory veto gates — evaluate BEFORE scoring price** (each must have primary written evidence or a correctly qualified and measured source test):
1. **Actual data fit:** symbol-level SPY/BIL daily raw executable OHLC for agreed sample, cash dividends/ex dates, all splits/reverse splits, corporate-action methodology, missing-date policy and verifiable coverage.
2. **Contract and privacy fit:** authorized internal commercial backtest, non-generative statistical forecasting, permitted team access, storage/backups, independent audit and exact deletion rights after termination; no raw licensed data sent to external LLM/agent services without authorized terms.
3. **PIT and execution fit:** precise vendor first-availability/revision times or conservative precommitted delays, as-of feature integrity at frozen 16:00 ET cutoff; next-session executable trade price can be reconstructed without lookahead.
4. **Operational fit:** stable documented API/delivery, provenance/revisions, maintenance burden, incident handling, outage fallback and source replacement path.
5. **Lifecycle economics fit:** complete quote for internal seats, exchange pass-through, research vs third-party redistribution, integrations, audit/retention add-ons, storage, support and termination; one-month pilot only if it actually permits required data uses.

**Gate outcomes:** PASS/FAIL/BLOCKED per gate. Any FAIL -> SOURCE_NO_GO; any BLOCKED -> no purchase or Gate 0 upgrade. No low price may override a gate. For suppliers that *all* pass, compare on an agreed qualitative priority hierarchy: accuracy/coverage and PIT evidence first, legal/reproducibility second, operational support third, 12/24-month total cost fourth. Do not produce a falsely precise weighted score without measured inputs.

**Supplier evidence table (currently; not procurement approval)**:
| Source | Current status | Reason |
|---|---|---|
| Public Fed/Treasury/BIS | FREE_SOURCE_RESEARCH_CANDIDATE | Publicly obtainable macro series, still require source-specific rights and release-time validation |
| Kenneth French Fama/French 3-factor | PUBLICLY_LISTED / RIGHTS_NOT_CLEARED / EXPLORATORY_ONLY | Monthly TXT/CSV and historical archives publicly advertised, but CRSP-derived Mkt-RF and ICE-derived RF, no independent business-model license confirmation. As of Jan 2025, French switched US research returns from FIZ to CIZ with different dividend reinvestment timing; may affect historical comparisons |
| Tiingo Power Commercial | CONDITIONAL / NOT_SELECTED | $50/mo, possible raw OHLC/divCash/splitFactor; source-by-symbol availability, historic 16:00 vintages, cancellation evidence retention, AI/vendor restrictions unconfirmed |
| Twelve Data Business Venture | CONDITIONAL / NOT_SELECTED | Price $149/mo starting level; exact feature/rights and sample completeness unknown |
| EODHD Commercial Internal | CONDITIONAL / NOT_SELECTED | Price $399/mo; source/version and rights unconfirmed |
| SSGA NAV XLSX | STANDALONE_EXECUTABLE_RETURN_NO_GO | Already checked: NAV only, no market OHLC/dividends/splits; workbook rights restrictions |

**Read-only follow-up research completed without data download**:
- French source: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html lists factor datasets as TXT/CSV and monthly historical archives. It explicitly records 2025-01 change from CRSP FIZ to CIZ and monthly-return reinvestment methodology change. Definition: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_factors.html defines `Rm-Rf` as CRSP market minus one-month bill rate; RF is ICE BofA from June 2024.
- This confirms *availability and methodological changes*, NOT legal permission for persistent commercial/AI ingestion, immutable PIT vintages or direct tradable ETF returns.
- Tiingo publicly advertises $50/mo or $499/yr for internal commercial use: https://www.tiingo.com/about/pricing ; model/AI restrictions: https://www.tiingo.com/tos/ . Price is a screening datum, not a provider recommendation.

**Next authorized activity**: preserve the no-paid policy, document minimal source-agnostic synthetic format and read-only source-license inquiry; only evaluate real-source imports after source rights are verified. Formal R2/backtests, live trades, vendor payments, deployments and merges remain unapproved. No user action presently required.
