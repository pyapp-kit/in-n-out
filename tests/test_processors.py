from in_n_out import get_processor, set_processors


def test_set_processor():
    with set_processors({int: 2}):
        assert get_processor(int)() == 2
