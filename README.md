# Protocols

No gatekeepers. No custodians.

Independent, rigorous analysis of cross-chain and same-chain swap protocols,
in the spirit of L2Beat. Each protocol is held to the ideal: anyone can use it,
and you remain sovereign over your funds throughout. We read the deployed
contracts and call the live services to find where a protocol departs from
that ideal, facet by facet.

Published at **[docs.mailam.app/protocols](https://docs.mailam.app/protocols/)**.

## What's here

- **`products/`**: one entry per protocol, a YAML header of facts and the notes
  behind them. The site turns each header into a seven-petal rosette.
- **The model:**
  - `CONSTRAINT.md`: the test every exit is held to.
  - `DESIGN_IMPLICATIONS.md`: what it means for a system built on these
    protocols.
  - `CRITERIA.md`: the facets each entry records and how the petals are rated.
  - `METHOD.md`: how to research and write an entry.
- **`GASLESS.md`**: how each major token can be moved from an account that
  holds no native gas, read on-chain.

Ratings describe and never exclude: a red petal says what can go wrong, not that
a protocol shouldn't be used.

## Building the site

```sh
pip install pyyaml        # also needs pandoc
make                      # writes _site/
make serve                # builds, then serves it at localhost:8000
```

Every push to `main` publishes it through GitHub Pages
(`.github/workflows/pages.yml`).
