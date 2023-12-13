# Getting Started

## Providers, Processors, and Stores

`in-n-out` is a dependency injection framework for Python.  It allows
you to write functions using type annotations, and then inject
dependencies into those functions at call time. Two important concepts
in `in-n-out` are *providers* and *processors*.

- **Providers** are functions that may be called with no arguments
  and return an instance of a type.
- **Processors** are functions that take an instance of a type and
  do something with it.

A [`Store`][in_n_out.Store] is a collection of providers and processors.
You will usually begin by creating a `Store` instance to manage your providers and
processors. More than one provider/processor can be registered per type.

```python
from in_n_out import Store

store = Store.create('my-store')
```

This store can be retrieved later using `Store.get_store`, and
destroyed using `Store.destroy`.

```python
store = Store.get_store('my-store')

# Store.destroy('my-store') # would destroy the store... but we still want it :)
```

!!!info "The global store"
    For convenience, any store methods accessed at the top level namespace will
    use a global store, unless a store name or instance is passed

## Registering Providers

Dependency inject works by providing an instance of a type to a function
or method that requires it.  Let's begin by declaring some type that will be
important to our application:

```python
class Thing:
    """Some thing I care about."""
    def __init__(self, name: str):
        self.name = name
```

Providers are registered using the [`Store.register_provider`][in_n_out.Store.register_provider].  They are functions that may be called with no arguments
and return an instance of a type.  `in-n-out` will inspect the type annotations
of the function to determine what type it provides.

```python
import in_n_out as ino

def heres_the_thing() -> Thing:
    return Thing("Thing")

# register a provider of Thing
store.register_provider(heres_the_thing)
```

!!!tip "decorators"
    Registration functions may also be used as decorators:

    ```python
    @store.register_provider
    def heres_the_thing() -> Thing:
        return Thing("Thing")
    ```

!!!note
    If you prefer not to use type annotations, or prefer to be explicit about
    the type the provider provides, you may pass a `type_hint` argument:

    ```python
    store.register_provider(heres_the_thing, Thing)
    ```

### Injecting dependencies into functions

Once you have registered a provider, you can use it to inject dependencies
into functions.  Let's say we have a function that can use a `Thing`:

```python
def get_things_name(thing: Thing) -> str:
    return thing.name
```

Naturally, this function will fail if we try to call it without providing
a `Thing`:

```python
get_things_name()
# TypeError: get_things_name() missing 1 required positional argument: 'thing'
```

We can use the [`Store.inject`][in_n_out.Store.inject] method to inject a `Thing` into the function.
More than one provider per type can be registered. The store will iterate through all
providers registered for the required type, stopping at the first one that returns an
object that is not `None`.

Providers should return `None` if it is not able to provide the requested object as
this allows `in-n-out` to continue iterating through any other registered providers:

```python
get_things_name = store.inject(get_things_name)
print(get_things_name())  # prints "Thing"
```

!!!tip "decorators"
    As with registration functions, we can use `Store.inject` as a decorator:

    ```python
    @store.inject
    def get_things_name(thing: Thing) -> str:
        if hasattr(thing, name):
            return thing.name
        return None

    print(get_things_name())  # prints "Thing"
    ```

If the store is unable to find a provider for a required type, it will raise
an exception:

```python
@store.inject
def give_me_a_string(s: str) -> str:
    return s

give_me_a_string()
# TypeError: After injecting dependencies for NO arguments,
#   give_me_a_string() missing 1 required positional argument: 's'
```

### Weights and provider priority

When you are registering multiple providers for the same type, you can use the
`weight` parameter to specify which providers should be tried first.

```python
def give_me_another_thing() -> Thing:
    return Thing("Another Thing")

store.register_provider(give_me_another_thing, weight=10)
print(get_things_name())  # prints "Another Thing"
```

### Temporary registration

Registration functions may be used as context managers to temporarily register
providers.

```python
def most_important_thing() -> Thing:
    return Thing("Most Important Thing")

with store.register_provider(most_important_thing, weight=20):
    print(get_things_name())  # prints "Most Important Thing"
print(get_things_name())  # prints "Another Thing"
```

### Undoing registration

Alternatively, you can hang on to the object returned by the `register_provider`
function, and call its `cleanup` method:

```python
token = store.register_provider(most_important_thing, weight=20)
print(get_things_name())  # prints "Most Important Thing"

token.cleanup()  # unregister
print(get_things_name())  # prints "Another Thing"
```

## Processors

Processors are functions that take an instance of a type and do something
with it, usually for the purpose of side effects. Like providers, you can register
multiple processors per return type and the Store will iterate through all of
them. [`Store.register_processor`][in_n_out.Store.register_processor] will also
take a `weight` parameter that enables you to specify the order in which to
'process' the return objects.

If an error is raised when executing a processor, it will be passed as a warning
after the final processor has been run.

[`Store.inject_processors`][in_n_out.Store.inject_processors] will also take a
`first_processor_only` parameter that can be used to specify that only the
first processor should be used.

```python
@store.inject_processors
def get_things_name(thing: Thing) -> str:
    return thing.name

def greet_name(name: str):
    print(f"Hello, {name}!")

store.register_processor(greet_name)

get_things_name(Thing('Bob'))  # prints "Hello, Bob!"  (and still returns "Bob")
```

!!!warning "Careful"
    Naturally, you want to be a bit careful with processors. It would be rather
    unusual to register a processor for something as common as `str` as we
    did above. Or, at the very least, we wouldn't inject processors into a
    function that returned `str`.

## Real world example

Let's look at a more realistic example.

Suppose we have an application like a text editor or IDE that allows plugins to
provide functionality like syntax highlighting, code completion, etc.  We might
allow plugins to define functions that accept a `Document` and use it's API to
provide additional functionality.

Rather than asking plugins to call some `get_current_document()` function, we
can allow them to write functions that state their dependencies using type hints,
and then *we* (the application) determine how we will provide those dependencies.

```python title="some_plugin.py"
def highlight_document(document: Document):
    # do something with the document
    pass
```

```python title="my_application.py"
from in_n_out import Store

# create a store
store = Store.create('my-store')

# register a Document provider
@store.register_provider
def get_current_document() -> Document:
    # get the current document from somewhere
    ...

# somehow gather functionality from plugins
from some_plugin import highlight_document

plugin_functions = [highlight_document]

# inject dependencies into plugin functions
injected = [store.inject(f) for f in plugin_functions]
```

Now we can call the injected functions, and they will have access
to the current document.

### `app-model`

In a GUI, one often needs to be able to call functions in response to
user actions, such as selection of a menu item or a button click.
However, those commands usually want some additional arguments or
context.  Dependency injection provides a nice way to handle this
problem with loose coupling.

See [`app-model`](https://github.com/pyapp-kit/app-model) for an
example of a library that uses `in-n-out` to inject dependencies
into commands in the context of a GUI application.

## More information

See the [API documentation](reference/index.md) for greater detail on the
`Store` class and its methods.
