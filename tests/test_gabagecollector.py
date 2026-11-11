import os
import threading
from io import StringIO
from unittest.mock import Mock

import pytest
from pyexcel import iget_array
from pyexcel.internal import garbagecollector as gc

from .nose_tools import eq_


def test_cleanup_attempts_every_resource_and_raises_the_first_error(
    monkeypatch,
):
    monkeypatch.setattr(gc, "GARBAGE", gc._ThreadLocalGarbage())
    first_error = OSError("first close failed")
    first = Mock()
    second = Mock()
    last = StringIO("last resource")
    first.close.side_effect = first_error
    second.close.side_effect = RuntimeError("second close failed")
    for resource in (first, second, last):
        gc.append(resource)
    assert list(gc.GARBAGE) == [first, second, last]

    with pytest.raises(OSError) as raised:
        gc.free_resources()

    assert raised.value is first_error
    first.close.assert_called_once_with()
    second.close.assert_called_once_with()
    assert last.closed
    assert len(gc.GARBAGE) == 0
    gc.free_resources()
    first.close.assert_called_once_with()


def test_reset_forgets_resources_without_closing_them(monkeypatch):
    monkeypatch.setattr(gc, "GARBAGE", gc._ThreadLocalGarbage())
    with StringIO("owned by the caller") as stream:
        gc.append(stream)
        gc.reset()
        assert list(gc.GARBAGE) == []
        assert not stream.closed


def test_gc():
    gc.free_resources()
    data = iget_array(
        file_name=os.path.join("tests", "fixtures", "bug_01.csv"),
    )
    data = list(data)
    eq_(len(gc.GARBAGE), 1)
    gc.free_resources()
    assert len(gc.GARBAGE) == 0


def test_gc_custom():
    gc.free_resources()
    f = open(
        os.path.join("tests", "fixtures", "bug_01.csv"), "r", encoding="utf-8"
    )
    gc.append(f)
    eq_(len(gc.GARBAGE), 1)
    gc.free_resources()
    assert len(gc.GARBAGE) == 0


def test_gc_is_thread_local():
    gc.free_resources()
    ready = [threading.Event(), threading.Event()]
    first_done = threading.Event()
    failures = []

    def worker(index):
        try:
            handle = StringIO("data")
            gc.append(handle)
            eq_(len(gc.GARBAGE), 1)
            ready[index].set()
            ready[1 - index].wait(timeout=5)
            if index == 0:
                gc.free_resources()
                assert handle.closed
                first_done.set()
            else:
                first_done.wait(timeout=5)
                assert not handle.closed
                gc.free_resources()
                assert handle.closed
            assert len(gc.GARBAGE) == 0
        except Exception as exc:
            failures.append(exc)

    first = threading.Thread(target=worker, args=(0,))
    second = threading.Thread(target=worker, args=(1,))
    first.start()
    second.start()
    first.join()
    second.join()

    assert not failures
    assert len(gc.GARBAGE) == 0
