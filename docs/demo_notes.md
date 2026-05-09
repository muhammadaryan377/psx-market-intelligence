## PSX Market Intelligence Demo Notes

Run these checks after collecting news, creating embeddings, and streaming trend rows:

```powershell
python -m rag_layer.vector_store
python -m rag_layer.retriever
python -m sentiment_layer.sentiment_service
python -m agents.graph
python -m tests.test_spark_to_agents
```

The Spark replay data may contain older market dates while the demo RAG index
contains current 2026 news. Use a demo event-date override when you want the
Spark-to-agent test to retrieve the current news index:

```powershell
$env:DEMO_EVENT_DATE_OVERRIDE="2026-05-08"
python -m tests.test_spark_to_agents
```

Decision output is academic decision support only. It is not financial advice
and does not execute trades.

## DVC data remote

The project data is versioned with DVC and uses this Google Drive folder as the
default remote:

```powershell
dvc remote list
dvc status
dvc push
dvc pull
```

If Google Drive asks for authorization during `dvc push` or `dvc pull`, finish
the browser login for the same Google account that owns the shared Drive folder.
