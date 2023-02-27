# in-n-out

[![License](https://img.shields.io/pypi/l/in-n-out.svg?color=green)](https://github.com/pyapp-kit/in-n-out/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/in-n-out.svg?color=green)](https://pypi.org/project/in-n-out)
[![Python Version](https://img.shields.io/pypi/pyversions/in-n-out.svg?color=green)](https://python.org)
[![CI](https://github.com/pyapp-kit/in-n-out/actions/workflows/ci.yml/badge.svg)](https://github.com/pyapp-kit/in-n-out/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pyapp-kit/in-n-out/branch/main/graph/badge.svg)](https://app.codecov.io/gh/pyapp-kit/in-n-out)
[![Benchmarks](https://img.shields.io/badge/⏱-codspeed-%23FF7B53)](https://codspeed.io/pyapp-kit/in-n-out)

Python dependency injection you can taste.

A lightweight dependency injection and result processing framework
for Python using type hints. Emphasis is on simplicity, ease of use,
and minimal impact on source code.

```python
import in_n_out as ino


class Thing:
    def __init__(self, name: str):
        self.name = name


# use ino.inject to create a version of the function
# that will retrieve the required dependencies at call time
@ino.inject
def func(thing: Thing):
    return thing.name


def give_me_a_thing() -> Thing:
    return Thing("Thing")


# register a provider of Thing
ino.register_provider(give_me_a_thing)
print(func())  # prints "Thing"


def give_me_another_thing() -> Thing:
    return Thing("Another Thing")


with ino.register_provider(give_me_another_thing, weight=10):
    print(func())  # prints "Another Thing"
```

This also supports processing *return* values as well
(injection of intentional side effects):

```python

@ino.inject_processors
def func2(thing: Thing) -> str:
    return thing.name

def greet_name(name: str):
    print(f"Hello, {name}!")

ino.register_processor(greet_name)

func2(Thing('Bob'))  # prints "Hello, Bob!"
```

### Alternatives

Lots of other python DI frameworks exist, here are a few alternatives to consider:

- <https://github.com/ets-labs/python-dependency-injector>
- <https://github.com/google/pinject>
- <https://github.com/ivankorobkov/python-inject>
- <https://github.com/alecthomas/injector>
- <https://github.com/Finistere/antidote>
- <https://github.com/dry-python/returns>
- <https://github.com/adriangb/di>
