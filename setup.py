import contextlib
import os

import setuptools

ext_modules = None
if not os.getenv("SKIP_CYTHON"):
    with contextlib.suppress(ImportError):
        from Cython.Build import cythonize

        # For cython test coverage install with `make build-trace`
        compiler_directives = {"linetrace": os.getenv("CYTHON_TRACE", False)}

        # Set CFLAG to all optimizations (-O3)
        # Any additional CFLAGS will be appended.
        # Only the last optimization flag will have effect
        os.environ["CFLAGS"] = "-O3 " + os.environ.get("CFLAGS", "")

        ext_modules = cythonize(
            "src/in_n_out/*.py",
            exclude=["**/__init__.py"],
            nthreads=int(os.getenv("CYTHON_NTHREADS", 0)),
            language_level=3,
            compiler_directives=compiler_directives,
        )

setuptools.setup(
    ext_modules=ext_modules,
    package_dir={"": "src"},
)
