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


class FakeDeleteQuery:
    def __init__(self):
        self.deleted_id = None

    def eq(self, key, value):
        assert key == "id"
        self.deleted_id = value
        return self

    def execute(self):
        return None


class FakeInsertQuery:
    def __init__(self, table, client):
        self.table = table
        self.client = client

    def execute(self):
        if self.table == "experiments":
            return type("Result", (), {"data": [{"id": "experiment-1"}]})()
        if self.table == "trades":
            raise RuntimeError("trade insert failed")
        return type("Result", (), {"data": []})()


class FakeTable:
    def __init__(self, name, client):
        self.name = name
        self.client = client

    def insert(self, rows):
        return FakeInsertQuery(self.name, self.client)

    def delete(self):
        self.client.delete_query = FakeDeleteQuery()
        return self.client.delete_query


class FakeClient:
    def __init__(self):
        self.delete_query = None

    def table(self, name):
        return FakeTable(name, self)


def test_create_experiment_deletes_partial_row_when_child_insert_fails() -> None:
    client = FakeClient()
    repo = Repository(client=client)

    try:
        repo.create_experiment(
            params={"product_id": "BTC-USD"},
            metrics={"trade_count": 1},
            trades=[{"entry_time": datetime.now(timezone.utc)}],
            equity_points=[],
        )
    except RuntimeError:
        pass

    assert client.delete_query.deleted_id == "experiment-1"
