"""A2-R — four helpers returned `None` for two different answers.

`None` meant both "this object genuinely has no such record" and "the lookup failed, so whether it exists
is unknown". A caller that cannot separate them reports a thing it could not read as a thing that is not
there. That is the same class as a hole check reporting "I cannot say" as "clean", which is the finding
this whole line of work started from.

The helpers still return `None`, so no call site had to change. A caller that cares passes a `status`
dict and reads `status["outcome"]`: `ABSENT` or `UNREADABLE`. These tests inject a failure into each site
and assert the two are distinguishable, because a distinction nothing exercises is a comment.
"""
import io

import pytest

import forefst as F


def test_the_vocabulary_exists_and_the_two_are_different():
    assert F.ABSENT != F.UNREADABLE


def test_outcome_records_absent_without_a_reason():
    st = {}
    assert F._outcome(st, None) is None
    assert st["outcome"] == F.ABSENT
    assert "reason" not in st, "an absent result must not invent a failure reason"


def test_outcome_records_unreadable_with_the_reason():
    st = {}
    assert F._outcome(st, None, ValueError("page unreadable")) is None
    assert st["outcome"] == F.UNREADABLE
    assert "page unreadable" in st["reason"]


class _Boom:
    """Stands in for an unreadable volume: any attribute access raises."""

    def __getattr__(self, name):
        raise OSError("injected: the device went away")


def test_get_object_si_separates_unreadable_from_absent():
    st = {}
    assert F.get_object_si(_Boom(), 0, 4096, None, [1], status=st) is None
    assert st["outcome"] == F.UNREADABLE, "an unreadable object tree must not read as 'no $SI'"


def test_fetch_t40_backing_separates_unreadable_from_absent():
    st = {}
    assert F.fetch_t40_backing(_Boom(), 0, 4096, None, {0x600: [1]}, 0x600, 1, status=st) is None
    assert st["outcome"] == F.UNREADABLE, "a failed walk must not read as 'no backing record'"


def test_gpt_partition_detail_separates_unreadable_from_absent(tmp_path):
    """This one had a BARE `except Exception:` — the geometry silently became 'no GPT'."""
    st = {}
    assert F.gpt_partition_detail(str(tmp_path / "does-not-exist.raw"), status=st) is None
    assert st["outcome"] == F.UNREADABLE

    empty = tmp_path / "empty.raw"
    empty.write_bytes(b"\x00" * (4096 * 4))
    st2 = {}
    F.gpt_partition_detail(str(empty), status=st2)
    assert st2["outcome"] in (F.ABSENT, F.UNREADABLE)


class _BoomIO:
    """A volume whose reads fail. `roots` must be a LIST with a live entry, or the helper returns ABSENT
    before it ever touches the device -- the first version of this test did exactly that and asserted
    `outcome in (ABSENT, UNREADABLE)`, which the genuine-absent path satisfied without proving anything."""

    def seek(self, *a):
        raise OSError("injected: device gone")

    def read(self, *a):
        raise OSError("injected: device gone")


@pytest.mark.parametrize("fn,args", [
    ("alloc_capacity", (0, 4096, None, [[], [7]])),
    ("alloc_read_summary", (0, 4096, None, [[], [7]], 1)),
])
def test_allocator_helpers_report_a_read_failure_as_unreadable(fn, args):
    st = {}
    assert getattr(F, fn)(_BoomIO(), *args, status=st) is None
    assert st["outcome"] == F.UNREADABLE, f"{fn}: a failed read must not read as 'no summary'"
    assert "injected" in st["reason"]


@pytest.mark.parametrize("fn,args", [
    ("alloc_capacity", (0, 4096, None, [[], []])),
    ("alloc_read_summary", (0, 4096, None, [[], []], 1)),
])
def test_allocator_helpers_report_a_missing_root_as_absent(fn, args):
    """The other half of the distinction: genuinely absent must NOT claim a failure.

    The volume here READS fine -- it simply has no such allocator root. `alloc_capacity` reads the image
    size before anything else, so handing it an unreadable stub reports UNREADABLE quite correctly; using
    one here would have tested the wrong branch (it did, in the first version of this test)."""
    st = {}
    assert getattr(F, fn)(io.BytesIO(b"\x00" * (4096 * 8)), *args, status=st) is None
    assert st["outcome"] == F.ABSENT
    assert "reason" not in st


def test_callers_that_do_not_care_are_unchanged():
    """`status` is optional: every existing call site passes nothing and still gets None."""
    assert F.get_object_si(_Boom(), 0, 4096, None, [1]) is None
    assert F.gpt_partition_detail("/nonexistent/xyz.raw") is None
