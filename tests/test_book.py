import pyexcel as p
from pyexcel.book import to_book

from .nose_tools import eq_


def test_converting_an_existing_book_preserves_its_identity():
    book = p.Book({"data": [[1, 2]]})
    assert to_book(book) is book
    assert book.to_dict() == {"data": [[1, 2]]}
    iterator = iter(book)
    assert iter(iterator) is iterator
    assert next(iterator).array == [[1, 2]]


def test_a_dictionary_of_sheet():
    test_data = [["a", "b"]]

    book_dict = {"test": p.Sheet(test_data)}

    book = p.Book(book_dict)
    eq_(book.test.array, test_data)


def test_book_len():
    test_data = [["a", "b"]]

    book_dict = {"test": p.Sheet(test_data)}

    book = p.Book(book_dict)
    eq_(len(book.test.array), 1)


def test_sheet_ordering():
    test_data = [["a", "b"]]

    book_dict = {"first": test_data, "middle": test_data, "last": test_data}

    book = p.Book(book_dict)
    eq_(book.sheet_names(), ["first", "middle", "last"])
