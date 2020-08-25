# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import datetime

from swh.lister.core.indexing_lister import IndexingLister


class MockedIndexingListerDbPartitionIndices(IndexingLister):
    # Abstract Attribute boilerplate
    LISTER_NAME = "DbPartitionIndices"
    MODEL = type(None)

    # ABC boilerplate
    def get_next_target_from_response(self, *args, **kwargs):
        pass

    def __init__(self, num_entries, first_index, last_index):
        self.num_entries = num_entries
        self.first_index = first_index
        self.last_index = last_index

    def db_num_entries(self):
        return self.num_entries

    def db_first_index(self):
        return self.first_index

    def db_last_index(self):
        return self.last_index


def test_db_partition_indices():
    m = MockedIndexingListerDbPartitionIndices(
        num_entries=1000, first_index=1, last_index=10001,
    )
    assert m

    partitions = m.db_partition_indices(100)

    # 1000 entries with indices 1 - 10001, partitions of 100 entries
    assert len(partitions) == 10
    assert partitions[0] == (None, 1001)
    assert partitions[-1] == (9001, None)


def test_db_partition_indices_zero_first():
    m = MockedIndexingListerDbPartitionIndices(
        num_entries=1000, first_index=0, last_index=10000,
    )
    assert m

    partitions = m.db_partition_indices(100)

    # 1000 entries with indices 0 - 10000, partitions of 100 entries
    assert len(partitions) == 10
    assert partitions[0] == (None, 1000)
    assert partitions[-1] == (9000, None)


def test_db_partition_indices_small_index_range():
    m = MockedIndexingListerDbPartitionIndices(
        num_entries=5000, first_index=0, last_index=5,
    )
    assert m

    partitions = m.db_partition_indices(100)

    assert partitions == [(None, 1), (1, 2), (2, 3), (3, 4), (4, None)]


def test_db_partition_indices_date_indices():
    # 24 hour delta
    first = datetime.datetime.fromisoformat("2019-11-01T00:00:00+00:00")
    last = datetime.datetime.fromisoformat("2019-11-02T00:00:00+00:00")

    m = MockedIndexingListerDbPartitionIndices(
        # one entry per second
        num_entries=24 * 3600,
        first_index=first,
        last_index=last,
    )
    assert m

    # 3600 entries per partition => 1 partition per hour
    partitions = m.db_partition_indices(3600)

    assert len(partitions) == 24

    expected_bounds = [first + datetime.timedelta(hours=i) for i in range(25)]
    expected_bounds[0] = expected_bounds[-1] = None

    assert partitions == list(zip(expected_bounds[:-1], expected_bounds[1:]))


def test_db_partition_indices_float_index_range():
    m = MockedIndexingListerDbPartitionIndices(
        num_entries=10000, first_index=0.0, last_index=1.0,
    )
    assert m

    partitions = m.db_partition_indices(1000)

    assert len(partitions) == 10

    expected_bounds = [0.1 * i for i in range(11)]
    expected_bounds[0] = expected_bounds[-1] = None

    assert partitions == list(zip(expected_bounds[:-1], expected_bounds[1:]))


def test_db_partition_indices_uneven_int_index_range():
    m = MockedIndexingListerDbPartitionIndices(
        num_entries=5641, first_index=0, last_index=10000,
    )
    assert m

    partitions = m.db_partition_indices(500)

    assert len(partitions) == 5641 // 500

    for i, (start, end) in enumerate(partitions):
        assert isinstance(start, int) or (i == 0 and start is None)
        assert isinstance(end, int) or (i == 10 and end is None)
