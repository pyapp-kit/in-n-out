# In-N-Out

## Python dependency injection with flavor

`in-n-out` is a lightweight dependency injection framework for Python.

```python
import in_n_out as ino



@ino.inject_dependencies # (1)
def times_seven_to_str(number: int) -> str:
    return str(number * 7)


@ino.provider # (2)
def provide_number() -> int:
    return 6


@ino.processor # (3)
def process_string(string: str):
    print(
        "The answer to the ultimate question of life, "
        f"the universe, and everything is: {string}"
    )


assert times_seven_to_str() == 42  # (4)
# prints: "The asnwer to the ultimate question of life..."
```

1. **inject** a function with argument and/or return hints
2. declare **providers**: functions capable of returning an instance of a given type.
3. declare **processors**: functions capable of accepting/processing an instance of a given type.
4. call the injected function with no parameters.  The function will be called with the injected dependencies, and the output will be processed.


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

That's the gist of it. Continue on with [Usage](usage) to learn more!
