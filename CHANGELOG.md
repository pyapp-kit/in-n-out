# Changelog

## [0.1.7](https://github.com/pyapp-kit/in-n-out/tree/0.1.7) (2023-02-27)

[Full Changelog](https://github.com/pyapp-kit/in-n-out/compare/v0.1.6...0.1.7)

**Implemented enhancements:**

- feat: add logging [\#53](https://github.com/pyapp-kit/in-n-out/pull/53) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- fix: avoid recursion when a provider also uses processors [\#51](https://github.com/pyapp-kit/in-n-out/pull/51) ([tlambert03](https://github.com/tlambert03))
- fix: Fix README example [\#48](https://github.com/pyapp-kit/in-n-out/pull/48) ([davidbrochart](https://github.com/davidbrochart))

**Tests & CI:**

- test: add benchmarks [\#55](https://github.com/pyapp-kit/in-n-out/pull/55) ([tlambert03](https://github.com/tlambert03))
- chore: minor ruff updates [\#54](https://github.com/pyapp-kit/in-n-out/pull/54) ([tlambert03](https://github.com/tlambert03))
- ci: fix ci [\#49](https://github.com/pyapp-kit/in-n-out/pull/49) ([tlambert03](https://github.com/tlambert03))
- build: use ruff for linting, update pre-commit [\#45](https://github.com/pyapp-kit/in-n-out/pull/45) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- ci\(dependabot\): bump actions/setup-python from 3 to 4 [\#56](https://github.com/pyapp-kit/in-n-out/pull/56) ([dependabot[bot]](https://github.com/apps/dependabot))
- chore: rename napari org to pyapp-kit [\#43](https://github.com/pyapp-kit/in-n-out/pull/43) ([tlambert03](https://github.com/tlambert03))

## [v0.1.6](https://github.com/pyapp-kit/in-n-out/tree/v0.1.6) (2022-11-09)

[Full Changelog](https://github.com/pyapp-kit/in-n-out/compare/v0.1.5...v0.1.6)

**Implemented enhancements:**

- feat: support python 3.11,  & disable typing tests [\#42](https://github.com/pyapp-kit/in-n-out/pull/42) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- fix: improve error message on failed injection [\#37](https://github.com/pyapp-kit/in-n-out/pull/37) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- ci: add app-model test [\#36](https://github.com/pyapp-kit/in-n-out/pull/36) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- ci\(dependabot\): bump styfle/cancel-workflow-action from 0.10.1 to 0.11.0 [\#40](https://github.com/pyapp-kit/in-n-out/pull/40) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump styfle/cancel-workflow-action from 0.10.0 to 0.10.1 [\#39](https://github.com/pyapp-kit/in-n-out/pull/39) ([dependabot[bot]](https://github.com/apps/dependabot))

## [v0.1.5](https://github.com/pyapp-kit/in-n-out/tree/v0.1.5) (2022-08-14)

[Full Changelog](https://github.com/pyapp-kit/in-n-out/compare/v0.1.4...v0.1.5)

**Fixed bugs:**

- fix: pass namespace through all type resolution functions [\#35](https://github.com/pyapp-kit/in-n-out/pull/35) ([tlambert03](https://github.com/tlambert03))

## [v0.1.4](https://github.com/pyapp-kit/in-n-out/tree/v0.1.4) (2022-08-12)

[Full Changelog](https://github.com/pyapp-kit/in-n-out/compare/v0.1.3...v0.1.4)

**Implemented enhancements:**

- feat: add on\_unresolved\_required\_args="ignore" to inject\(\) [\#33](https://github.com/pyapp-kit/in-n-out/pull/33) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- test: add typing tests [\#29](https://github.com/pyapp-kit/in-n-out/pull/29) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- chore: changelog v0.1.4 [\#34](https://github.com/pyapp-kit/in-n-out/pull/34) ([tlambert03](https://github.com/tlambert03))

## [v0.1.3](https://github.com/pyapp-kit/in-n-out/tree/v0.1.3) (2022-07-15)

[Full Changelog](https://github.com/pyapp-kit/in-n-out/compare/v0.1.2...v0.1.3)

**Fixed bugs:**

- fix: fix functools.wrapped functions [\#28](https://github.com/pyapp-kit/in-n-out/pull/28) ([tlambert03](https://github.com/tlambert03))

## [v0.1.2](https://github.com/pyapp-kit/in-n-out/tree/v0.1.2) (2022-07-13)

[Full Changelog](https://github.com/pyapp-kit/in-n-out/compare/v0.1.1...v0.1.2)

**Merged pull requests:**

- ci\(dependabot\): bump pypa/cibuildwheel from 2.7.0 to 2.8.0 [\#26](https://github.com/pyapp-kit/in-n-out/pull/26) ([dependabot[bot]](https://github.com/apps/dependabot))
- feat: add support for injecting into unbound methods [\#25](https://github.com/pyapp-kit/in-n-out/pull/25) ([tlambert03](https://github.com/tlambert03))

## [v0.1.1](https://github.com/pyapp-kit/in-n-out/tree/v0.1.1) (2022-07-06)

[Full Changelog](https://github.com/pyapp-kit/in-n-out/compare/v0.1.0...v0.1.1)

**Merged pull requests:**

- refactor: cleanup docs and api [\#24](https://github.com/pyapp-kit/in-n-out/pull/24) ([tlambert03](https://github.com/tlambert03))
- refactor: Unify API, and documentation [\#22](https://github.com/pyapp-kit/in-n-out/pull/22) ([tlambert03](https://github.com/tlambert03))
- feat: split decorator into 2 [\#20](https://github.com/pyapp-kit/in-n-out/pull/20) ([tlambert03](https://github.com/tlambert03))

## [v0.1.0](https://github.com/pyapp-kit/in-n-out/tree/v0.1.0) (2022-07-06)

[Full Changelog](https://github.com/pyapp-kit/in-n-out/compare/78b545996ae08fae199e8c81295cdedb24b86fe1...v0.1.0)

**Merged pull requests:**

- feat: allow register\_p\* to take only the function [\#19](https://github.com/pyapp-kit/in-n-out/pull/19) ([tlambert03](https://github.com/tlambert03))
- feat: prevent strong reference to bound methods [\#18](https://github.com/pyapp-kit/in-n-out/pull/18) ([tlambert03](https://github.com/tlambert03))
- fix: deal with partials [\#17](https://github.com/pyapp-kit/in-n-out/pull/17) ([tlambert03](https://github.com/tlambert03))
- feat: allow hashable types to be used as direct hits [\#16](https://github.com/pyapp-kit/in-n-out/pull/16) ([tlambert03](https://github.com/tlambert03))
- feat: put injection decorator on store [\#15](https://github.com/pyapp-kit/in-n-out/pull/15) ([tlambert03](https://github.com/tlambert03))
- ci: \[pre-commit.ci\] autoupdate [\#14](https://github.com/pyapp-kit/in-n-out/pull/14) ([pre-commit-ci[bot]](https://github.com/apps/pre-commit-ci))
- feat: Allow multiple provider/processors with weights [\#13](https://github.com/pyapp-kit/in-n-out/pull/13) ([tlambert03](https://github.com/tlambert03))
- feat: handle unions [\#12](https://github.com/pyapp-kit/in-n-out/pull/12) ([tlambert03](https://github.com/tlambert03))
- build: add cibuildwheel [\#10](https://github.com/pyapp-kit/in-n-out/pull/10) ([tlambert03](https://github.com/tlambert03))
- feat: add more validation for processors and providers, type cleanup [\#9](https://github.com/pyapp-kit/in-n-out/pull/9) ([tlambert03](https://github.com/tlambert03))
- test: add benchmarks [\#8](https://github.com/pyapp-kit/in-n-out/pull/8) ([tlambert03](https://github.com/tlambert03))
- feat: inject store namespace [\#7](https://github.com/pyapp-kit/in-n-out/pull/7) ([tlambert03](https://github.com/tlambert03))
- feat: make multiple store instances accessible [\#6](https://github.com/pyapp-kit/in-n-out/pull/6) ([tlambert03](https://github.com/tlambert03))
- test: add tests and big refactor [\#5](https://github.com/pyapp-kit/in-n-out/pull/5) ([tlambert03](https://github.com/tlambert03))
- feat: add cython option [\#4](https://github.com/pyapp-kit/in-n-out/pull/4) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump styfle/cancel-workflow-action from 0.9.1 to 0.10.0 [\#3](https://github.com/pyapp-kit/in-n-out/pull/3) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump codecov/codecov-action from 2 to 3 [\#1](https://github.com/pyapp-kit/in-n-out/pull/1) ([dependabot[bot]](https://github.com/apps/dependabot))



\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
