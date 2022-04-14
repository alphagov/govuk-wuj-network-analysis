# `govuk-wuj-network-analysis`

Using Network Analysis to define a set of pages related to a Whole User Journey (WUJ).

The final output is a Google Colab notebook `page_detector.ipynb`. The `Page Detector` first creates a functional graph of GOV.UK pages based on user movement. This graph is first defined by seed pages that are considered key pages in the WUJ. Pages that are hyperlinked from these seed pages are next included. Where a user visits at least one seed or hyperlinked page, all pages they visit in a session are included. This ultimately creates a functional subgraph of GOV.UK associated with user movement from key pages in a WUJ. We then use a biased random walks approach whose probability to move from a node (i.e. page) to one of its neighbours is based on the proportion of real user sessions that move from that particular page to its neighbours. A ranking method (page frequency-path frequency) is applied to rank a subset of pages associated with a particular WUJ.

```{warning}
Where this documentation refers to the root folder we mean where this README.md is
located.
```

## Getting started

To start using this project, [first make sure your system meets its
requirements](#requirements).

The functional network is based on user movement data and therefore retrives data from Google BigQuery. As such, Google BigQuery credentials are required to run the `Page Detector`.

### Requirements

```{note} Requirements for contributors
[Contributors have some additional requirements][contributing]!
```

- Python 3.6.1+ installed
- a `.secrets` file with the [required secrets and
  credentials](#required-secrets-and-credentials)
- [load environment variables][docs-loading-environment-variables] from `.envrc`
- Google BigQuery credentials

To install the Python requirements, open your terminal and enter:

```shell
pip install -r requirements.txt
```

## Required secrets and credentials

To run this project, [you need a `.secrets` file with secrets/credentials as
environmental variables][docs-loading-environment-variables-secrets]. The
secrets/credentials should have the following environment variable name(s):

| Secret/credential | Environment variable name | Description                                |
|-------------------|---------------------------|--------------------------------------------|
| Secret 1          | `SECRET_VARIABLE_1`       | Plain English description of Secret 1.     |
| Credential 1      | `CREDENTIAL_VARIABLE_1`   | Plain English description of Credential 1. |

Once you've added, [load these environment variables using
`.envrc`][docs-loading-environment-variables].

## Licence

Unless stated otherwise, the codebase is released under the MIT License. This covers
both the codebase and any sample code in the documentation. The documentation is ©
Crown copyright and available under the terms of the Open Government 3.0 licence.

## Contributing

[If you want to help us build, and improve `govuk-wuj-network-analysis`, view our
contributing guidelines][contributing].

## Acknowledgements

[This project structure is based on the `govcookiecutter` template
project][govcookiecutter].

[contributing]: ./docs/contributor_guide/CONTRIBUTING.md
[govcookiecutter]: https://github.com/best-practice-and-impact/govcookiecutter
[docs-loading-environment-variables]: ./docs/user_guide/loading_environment_variables.md
[docs-loading-environment-variables-secrets]: ./docs/user_guide/loading_environment_variables.md#storing-secrets-and-credentials
