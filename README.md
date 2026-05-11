# PSX Real-Time AI-Powered Market Intelligence System

Week 2 baseline for a Pakistan Stock Exchange market intelligence pipeline.

This repository is intentionally scoped to a stable data, Kafka, Spark, RAG,
sentiment, and test baseline. Final dashboard UX, final LangGraph orchestration,
brokerage execution, live licensed PSX APIs, and advanced ML are Week 3+ work.

## Week 2 Completed Scope

- Historical/sample PSX OHLCV data is organized under `data/`.
- Kafka producer can replay `data/sample_psx_data.csv` or `data/historical/*.csv`.
- Kafka topic setup and simple consumer are available for smoke testing.
- PySpark Structured Streaming reads Kafka JSON, cleans rows, detects trends, and writes processed trend output.
- Spark has a Windows-compatible local Hadoop/winutils setup path.
- RAG baseline loads `data/psx_news.csv` and uses FAISS/sentence-transformers when available, with TF-IDF or keyword fallback.
- Sentiment baseline uses VADER/TextBlob when available, with rule-based fallback.
- Agent imports are stable through a simple Week 2 sequential adapter.
- Flask app starts with a `/health` route.
- Tests run with graceful skips for unavailable local Spark/Kafka pieces.

## Folder Summary

- `config/` - project-root paths, Kafka settings, Spark settings.
- `data_sources/` and `scripts/` - PSX historical data collection/finalization helpers.
- `kafka_layer/` - producer, consumer, topic setup.
- `spark_layer/` - cleaning, trend detection, stream processor, output writer.
- `rag_layer/` - news loader, embedding/index builder, vector/TF-IDF store, retriever.
- `sentiment_layer/` - sentiment model and service fallback baseline.
- `agents/` - Week 2 adapters/placeholders; final LangGraph workflow is Week 3.
- `tests/` - baseline unit/smoke tests.
- `data/` - DVC-tracked datasets and local runtime outputs.

## Setup

```powershell
cd C:\Users\malik\Desktop\PSX-Intelligence-System
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Default `.env` values:

```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=psx-market-data
SPARK_APP_NAME=PSX Kafka Stream Processor
SPARK_CHECKPOINT_LOCATION=data/checkpoints/psx_stream_processor
PSX_STREAM_MODE=manual
PSX_PRODUCER_SOURCE=sample
```

## Run Kafka

```powershell
docker compose up -d
python -m kafka_layer.topics_setup
```

Optional consumer smoke test:

```powershell
python -m kafka_layer.consumer
```

## Run Producer

Replay the sample CSV:

```powershell
python -m kafka_layer.producer
```

Replay historical files:

```powershell
$env:PSX_PRODUCER_SOURCE="historical"
python -m kafka_layer.producer
```

Useful producer knobs:

```powershell
$env:PSX_PRODUCER_DELAY_SECONDS="0.05"
$env:PSX_PRODUCER_MAX_ROWS="500"
```

## Run Spark Stream

In a second terminal after Kafka is running:

```powershell
python -m spark_layer.stream_processor
```

or:

```powershell
python run_spark_stream.py
```

Output is written to:

```text
data/processed/psx_trends
```

Checkpoint state is written to:

```text
data/checkpoints/psx_stream_processor
```

## RAG Baseline

Build or refresh the vector/TF-IDF index:

```powershell
python -m rag_layer.create_embeddings
```

Query the retriever:

```powershell
python -m rag_layer.retriever "HBL price down reason"
```

If FAISS and sentence-transformers are installed, dense search is used. If not,
the system falls back to TF-IDF or keyword retrieval over `data/psx_news.csv`.

## Sentiment Baseline

```powershell
python -m sentiment_layer.sentiment_service
```

The output includes:

- `label`: `Positive`, `Negative`, or `Neutral`
- `score`: numeric sentiment score
- `sentiment_confidence`: aggregate confidence hint

## Flask Health Check

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000/health
```

## Tests

```powershell
python -m pytest tests
```

Kafka integration is not required for unit tests. Spark tests skip gracefully if
a local Spark session cannot start.

## Historical Data Helpers

Small 10-symbol historical collection:

```powershell
python -m data_sources.psxdata_client
python -m data_sources.clean_psx_data
```

100-stock data finalization:

```powershell
python scripts/finalize_100_stocks_data.py
```

The finalizer uses `psxdata`, filters common stocks, writes metadata under
`data/metadata/`, raw daily prices under `data/raw/prices_daily/`, and processed
100-stock output under `data/processed/`.

## Known Limitations

- Kafka must be running locally for producer/consumer/stream integration.
- Spark Kafka connector download can depend on local Maven/Ivy cache and network.
- The default stream mode is `manual`, which uses `kafka-python` polling before
  passing micro-batches into Spark. Set `PSX_STREAM_MODE=structured` to force
  Spark's native Kafka source.
- RAG quality depends on the current `data/psx_news.csv` coverage.
- Sentiment is a Week 2 baseline, not a trained PSX-specific model.
- The Flask dashboard is intentionally minimal.

## Week 3 TODO

- Build the final real-time Flask/dashboard UI.
- Replace the sequential agent adapter with the final LangGraph workflow.
- Connect Spark trend events to agent processing as a live service.
- Add richer explanation and audit views.
- Add model evaluation and more robust finance-specific sentiment.
- Keep brokerage/trading execution out of scope unless explicitly required later.
