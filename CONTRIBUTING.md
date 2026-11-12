# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Contributing Code

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `master`.
2. If you've changed something, update the documentation.
3. Issue a pull request

By contributing, you agree that your contributions will be licensed under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project.
Feel free to contact the maintainers if that's a concern.

## V3 change review

For V3 work, use the canonical development branch and follow [branch governance](docs/BRANCH_GOVERNANCE.md). Every change follows the [simplify-before-adding principle](docs/V3_ARCHITECTURE_CLOSURE.md#mandatory-engineering-principle--simplify-before-adding): reuse the existing owner, remove duplication where relevant, justify any additional complexity, and report regression evidence and remaining limitations in the PR. No additional approval workflow is required.

## Coding Style

This project uses [black](https://github.com/ambv/black) to ensure the code follows a consistent style.

## Report bugs using Github's issues

GitHub issues are used to track public bugs. Report a bug by [opening a new issue](../../issues/new/choose)

## Write bug reports with details

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)
