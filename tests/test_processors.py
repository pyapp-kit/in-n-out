# from typing import Optional, Sequence

# import pytest

# from in_n_out import get_processor, processor, set_processors
# from in_n_out._processors import clear_processors

# @pytest.mark.parametrize(
#     "type, provide, ask_type, expect",
#     [
#         (int, lambda: 1, int, 1),  # processor can be a function
#         (int, 1, int, 1),  # or a constant value
#         (Sequence, [], list, []),  # we can ask for a subclass of a provided types
#     ],
# )
# def test_set_processors(type, provide, ask_type, expect):
#     """Test that we can set processor as either function or constant, and get it back."""
#     assert not get_processor(ask_type)
#     with set_processors({type: provide}):
#         assert get_processor(ask_type)() == expect
#     assert not get_processor(ask_type)  # make sure context manager cleaned up


# def test_set_processors_cleanup():
#     """Test that we can set processors in contexts, and cleanup"""
#     assert not get_processor(int)

#     with set_processors({int: 1}):
#         assert get_processor(int)() == 1
#         with pytest.raises(ValueError, match="already has a processor and clobber is"):
#             set_processors({int: 2})
#         with set_processors({int: 2}, clobber=True):
#             assert get_processor(int)() == 2
#         assert get_processor(int)() == 1

#     assert not get_processor(int)


# def test_processor_decorator():
#     """Test the @processor decorator."""
#     assert not get_processor(int)

#     @processor
#     def provides_int() -> int:
#         return 1

#     assert get_processor(int) is provides_int
#     assert get_processor(int)() == 1

#     clear_processor(int)
#     assert not get_processor(int)

#     with pytest.warns(UserWarning, match="No processor was registered"):
#         clear_processor(int, warn_missing=True)


# def test_optional_processors():
#     """Test providing & getting Optional[type]."""
#     assert not get_processor(Optional[int])
#     assert not get_processor(str)

#     @processor
#     def provides_optional_int() -> Optional[int]:
#         return 1

#     @processor
#     def provides_str() -> str:
#         return "hi"

#     # we don't have a processor guaranteed to return an int
#     assert not get_processor(int)
#     # just an optional one
#     assert get_processor(Optional[int]) is provides_optional_int

#     # but provides_str returns a string
#     assert get_processor(str) is provides_str
#     # which means it also provides an Optional[str]
#     assert get_processor(Optional[str]) is provides_str

#     # also register a processor for int
#     @processor
#     def provides_int() -> int:
#         return 1

#     assert get_processor(int) is provides_int
#     # the definite processor takes precedence
#     # TODO: consider this...
#     assert get_processor(Optional[int]) is provides_int

#     # TODO: consider this
#     # when clearing `int` would get rid of `provides_optional_int` AND `provides_int`
#     # but clearing Optional[int] would only get rid of `provides_optional_int`
#     assert clear_processor(Optional[int]) is provides_optional_int
#     assert clear_processor(int) is provides_int
#     assert clear_processor(str) is provides_str

#     # all clear
#     assert not _OPTIONAL_processorS
#     assert not _processorS
