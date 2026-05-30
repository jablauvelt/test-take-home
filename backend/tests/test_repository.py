from datetime import datetime, timezone

from app.repository import PAGE_SIZE, Repository


class FakePagedQuery:
    def __init__(self, pages):
        self.pages = pages
        self.ranges = []

    def range(self, start, end):
        self.ranges.append((start, end))
        return self

    def execute(self):
        page_index = len(self.ranges) - 1

        class Result:
            data = self.pages[page_index]

        return Result()


def test_execute_all_reads_until_short_page() -> None:
    query = FakePagedQuery(
        [
            [{"id": index} for index in range(PAGE_SIZE)],
            [{"id": PAGE_SIZE}],
        ]
    )
    repo = Repository(client=None)

    rows = repo._execute_all(query)

    assert len(rows) == PAGE_SIZE + 1
    assert query.ranges == [(0, 999), (1000, 1999)]


def test_serialize_row_converts_datetimes_to_isoformat() -> None:
    repo = Repository(client=None)
    now = datetime(2026, 5, 30, 18, tzinfo=timezone.utc)

    assert repo._serialize_row({"time": now, "price": 100}) == {
        "time": "2026-05-30T18:00:00+00:00",
        "price": 100,
    }

