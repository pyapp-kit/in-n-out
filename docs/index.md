# In-N-Out

## Python dependency injection with flavor

`in-n-out` is a lightweight dependency injection framework for Python.

```python
import in_n_out as ino

@ino.inject_dependencies
def square(number: int):
    return number**2

with ino.set_providers({int: lambda: 4}):
    # call with no parameters
    assert square() == 16
```

## What is dependency injection?

This [stack overflow post](https://stackoverflow.com/questions/130794/what-is-dependency-injection)
explains dependency injection in a more general sense, but begins by citing [James Shore](https://www.jamesshore.com/v2/blog/2006/dependency-injection-demystified) who summed it up as follows.

> "Dependency Injection" is a 25-dollar term for a 5-cent concept ... it means giving an object its instance variables.

That wording comes from the Java world, so for the purposes of this python library (which focuses on *function* inputs and outputs), we can say this:

!!! important "Key idea"
    **Dependency injection lets you state *what* your function requires, without knowing ahead of time where it will come from... and even
    *call* it without providing parameters.**

### Without dependency injection

For example, imagine we have the following `Person` object:

```python
class Person:
    def __init__(self, name: str):
        self.name = name
```

we also have a function that operates on a `Person` (and declares so by using a [type annotation](https://docs.python.org/3/library/typing.html)):

```python
def greet(person: Person):
    print("Hello, " + person.name)
```

To use this function, we need to have a `Person` *instance*:

```python
>>> john = Person("John")
>>> greet(john) # Hello, John
```

### Dependency injection with `in-n-out`

That will suit us for the vast majority of use cases, but sometimes we need to
be able to call our function `greet` with "whatever the current person" may be
in some broader **context**. In other words, we'd like to inject some "current"
person as an argument to our function (*without the caller requiring a pointer to it to that person*).

``` python linenums="1"
import in_n_out as ino

@ino.inject_dependencies  # (1)
def greet(person: Person):
    print("Hello, " + person.name)


with ino.set_providers({Person: Person("Jerry")}):
    greet() # Hello, Jerry (2)

with ino.set_providers({Person: Person("Bob")}):
    greet() # Hello, Bob   (3)
```

1. `in_n_out.inject_dependencies` is a decorator that prepares a function for dependency injection.
2. :eyes: Look ma, no parameters provided!
3. :tada: Calling the same function in a different context gives us a different result!

<small>

- line 3: `in_n_out.set_providers` is a decorator that sets the providers for the injector.

- line 9: we can then call the function `greet` with no parameters: it will use the available providers within the current context to inject the dependencies.

</small>
