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
