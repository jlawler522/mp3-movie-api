import pandas as pd
import pytest

import main
from src import MovieStorage

MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]


def test_movies_persist(client, test_storage, uploaded_movies):
    reopened = MovieStorage(test_storage.db_path)
    df = reopened.get()

    assert reopened.count_movies() == 20
    assert len(df) == 20
    assert list(df.columns) == MOVIE_COLUMNS

    expected_titles = pd.read_csv("fixtures/sample_movies.csv")["title"].tolist()
    assert df["title"].tolist() == expected_titles

    stored_ids = [row["id"] for row in reopened.select_columns(["title"], limit=100)]
    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200
    api_ids = [row["id"] for row in response.json()["data"]]

    assert stored_ids == list(range(1, 21))
    assert api_ids == list(range(1, 21))


def test_cache_and_processing(client, uploaded_movies, processing_body):
    first_100 = client.get("/movies", params={"limit": 100})
    first_1 = client.get("/movies", params={"limit": 1})
    assert first_100.status_code == 200
    assert first_1.status_code == 200
    assert main.cache.get(100) == first_100.json()
    assert main.cache.get(1) == first_1.json()

    repeat_100 = client.get("/movies", params={"limit": 100})
    assert repeat_100.status_code == 200
    assert repeat_100.json() == first_100.json()

    processed = client.post("/movies/process", json=processing_body)
    assert processed.status_code == 200
    report = processed.json()
    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"]["rows_before"] == 20
    assert report["cleaning_report"]["rows_after"] == 16
    assert report["cleaning_report"]["rows_removed"] == 4
    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    after = client.get("/movies", params={"limit": 100})
    assert after.status_code == 200
    body = after.json()
    assert body["total_rows"] == 16
    assert [row["title"] for row in body["data"]] == [
        f"Movie {letter}" for letter in "ABCDEFGHIJKLMNOP"
    ]
    assert [row["id"] for row in body["data"]] == list(range(1, 17))
    assert main.cache.get(100) == body


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    first = client.get("/movies", params={"limit": 100})
    assert first.status_code == 200

    def fail_if_called(*args, **kwargs):
        pytest.fail("Database was queried on a cache hit")

    monkeypatch.setattr(main.storage, "select_columns", fail_if_called)
    monkeypatch.setattr(main.storage, "count_movies", fail_if_called)

    second = client.get("/movies", params={"limit": 100})
    assert second.status_code == 200
    assert second.json() == first.json()
