# in-n-out

Python dependency injection you can taste.  :fontawesome-solid-burger:

A lightweight dependency injection and result processing framework
for Python using type hints. Emphasis is on simplicity, ease of use,
and minimal impact on source code.

```python
import in_n_out as ino

# register functions that provide a dependency
@ino.register_provider
def some_number() -> int:
    return 42

# inject dependencies into functions
@ino.inject
def print_square(num: int):
    print(num ** 2)

print_square()  # prints 1764
```

See the [Getting Started](getting_started.md) guide for a quick introduction or
the [API Reference](reference/index.md) for detailed documentation.

## Installation

Install from pip

```bash
pip install in-n-out
```

Or from conda-forge

```bash
conda install -c conda-forge in-n-out
```
