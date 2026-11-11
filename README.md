# MP3 Movie API

This FastAPI application stores a single movie collection in SQLite and serves it through a REST API. `src/database.py` creates the SQLite connection and the `movies` table, and `src/storage.py` (`MovieStorage`) saves, retrieves, counts, and filters movies using SQL. `POST /upload` checks that a CSV has exactly the columns title, release_year, rating, and genre, then replaces the stored collection in one transaction. `GET /movies` returns stored rows with the total count, and `GET /movies/search` filters by minimum rating with SQL sorting and limits. `POST /movies/process` reuses the MP1 pipeline in `data_pipeline/` to validate and clean the stored movies, then saves the result back to SQLite. `src/cache.py` (`MovieCache`) caches `GET /movies` responses in FakeRedis for 90 seconds per limit, and every successful upload or processing run clears the cache so responses are never outdated. Because the data lives in `data/movies.db`, it survives server restarts.

## Run the API

```
python -m uvicorn main:app --reload
```

Then open http://127.0.0.1:8000/docs.

## Run the tests

```
python -m pytest tests -v
```

## Sample processing request

After uploading `fixtures/sample_movies.csv`, send `POST /movies/process` with:

```json
{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {"enabled": true, "axis": "rows"},
    "outliers": {"enabled": true, "columns": ["rating"], "method": "iqr", "threshold": 1.5}
  }
}
```

Expected result:

```json
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
```
