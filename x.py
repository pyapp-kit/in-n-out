import in_n_out as ino


class Person:
    def __init__(self, name: str):
        self.name = name


@ino.inject_dependencies
def greet(person: Person):
    print("Hello, " + person.name)


with ino.set_providers({Person: Person("Jerry")}):
    greet()

with ino.set_providers({Person: Person("Bob")}):
    greet()
