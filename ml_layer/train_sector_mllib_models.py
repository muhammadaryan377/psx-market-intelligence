from pathlib import Path
import re
import sys
import os

from pyspark.sql import SparkSession  # type: ignore
from pyspark.sql.functions import col, unix_timestamp, to_timestamp  # type: ignore

from pyspark.ml import Pipeline  # type: ignore
from pyspark.ml.feature import StringIndexer, VectorAssembler, StandardScaler  # type: ignore
from pyspark.ml.classification import (
    LogisticRegression,
    RandomForestClassifier,
)  # type: ignore
from pyspark.ml.evaluation import MulticlassClassificationEvaluator  # type: ignore


# ---------------------------------------------------------
# Windows Hadoop setup
# ---------------------------------------------------------
os.environ["HADOOP_HOME"] = r"C:\hadoop"
os.environ["PATH"] = r"C:\hadoop\bin;" + os.environ.get("PATH", "")


# ---------------------------------------------------------
# Project import setup
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from ml_layer.mllib_feature_engineering import create_features, FEATURE_COLS  # type: ignore


# ---------------------------------------------------------
# File paths
# ---------------------------------------------------------
INPUT_FILE = "data/processed/ml_training_prices.csv"

REPORT_FILE = Path("data/reports/sector_model_comparison.csv")
MODEL_DIR = Path("ml_layer/models/sector_models")


def create_spark_session():
    """
    Spark session create karta hai.
    """

    Path("C:/tmp/spark-warehouse").mkdir(parents=True, exist_ok=True)

    spark = (
        SparkSession.builder
        .appName("PSX_Sector_Wise_MLlib_Model_Training")
        .master("local[*]")
        .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
        .config("spark.sql.warehouse.dir", "file:///C:/tmp/spark-warehouse")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")
    return spark


def safe_name(name: str) -> str:
    """
    Sector ya model name ko folder-safe banata hai.
    Example:
    TECHNOLOGY & COMMUNICATION -> technology_communication
    """

    name = str(name).lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name


def time_based_split(df):
    """
    Time-series data ke liye random split nahi karte.
    Har sector ke andar old 80% dates training ke liye,
    latest 20% dates testing ke liye use hongi.
    """

    df = df.withColumn("date_ts", to_timestamp(col("date")))
    df = df.withColumn("date_num", unix_timestamp(col("date_ts")))
    df = df.dropna(subset=["date_num"])

    threshold = df.approxQuantile("date_num", [0.8], 0.01)[0]

    train_df = df.filter(col("date_num") <= threshold)
    test_df = df.filter(col("date_num") > threshold)

    return train_df, test_df


def evaluate_model(model_name, predictions):
    """
    Model metrics calculate karta hai.
    """

    accuracy_evaluator = MulticlassClassificationEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="accuracy",
    )

    precision_evaluator = MulticlassClassificationEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="weightedPrecision",
    )

    recall_evaluator = MulticlassClassificationEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="weightedRecall",
    )

    f1_evaluator = MulticlassClassificationEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="f1",
    )

    accuracy = accuracy_evaluator.evaluate(predictions)
    precision = precision_evaluator.evaluate(predictions)
    recall = recall_evaluator.evaluate(predictions)
    f1 = f1_evaluator.evaluate(predictions)

    print("\n" + "=" * 70)
    print(f"MODEL: {model_name}")
    print("=" * 70)
    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1-score : {f1:.4f}")

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def safe_save_model(model, save_path: Path, model_name: str) -> bool:
    """
    Spark ML model save karta hai.
    Agar Windows Hadoop save issue aaye to script crash nahi hogi.
    """

    try:
        model.write().overwrite().save(str(save_path))
        print(f"Saved {model_name} at: {save_path}")
        return True

    except Exception as e:
        print("\n" + "!" * 70)
        print(f"WARNING: Could not save {model_name}")
        print(f"Path: {save_path}")
        print("Training will continue.")
        print("Reason:", str(e)[:700])
        print("!" * 70)
        return False


def build_models():
    """
    2 MLlib models return karta hai:
    1. Logistic Regression
    2. Random Forest

    Slow multi-class wrapper model remove kiya gaya hai kyunki sector-wise
    training main har sector ke liye repeat hota hai aur bohot time leta hai.
    """

    return {
        "Logistic Regression": LogisticRegression(
            featuresCol="features",
            labelCol="label",
            family="multinomial",
            maxIter=50,
        ),

        "Random Forest": RandomForestClassifier(
            featuresCol="features",
            labelCol="label",
            numTrees=100,
            maxDepth=8,
            seed=42,
        ),
    }


def train_one_sector(sector_name: str, sector_df):
    """
    Ek sector ke liye fast models train + compare karta hai.
    """

    print("\n" + "#" * 90)
    print(f"TRAINING SECTOR: {sector_name}")
    print("#" * 90)

    sector_rows = sector_df.count()
    print("Sector rows:", sector_rows)

    if sector_rows < 300:
        print("Skipping sector: rows less than 300")

        return [
            {
                "sector": sector_name,
                "model_name": "SKIPPED",
                "accuracy": None,
                "precision": None,
                "recall": None,
                "f1": None,
                "rows": sector_rows,
                "status": "skipped_rows_less_than_300",
            }
        ]

    print("\nTarget distribution:")
    sector_df.groupBy("target").count().show()

    target_classes = sector_df.select("target").distinct().count()

    if target_classes < 2:
        print("Skipping sector: target has fewer than 2 classes")

        return [
            {
                "sector": sector_name,
                "model_name": "SKIPPED",
                "accuracy": None,
                "precision": None,
                "recall": None,
                "f1": None,
                "rows": sector_rows,
                "status": "skipped_less_than_2_classes",
            }
        ]

    train_df, test_df = time_based_split(sector_df)

    train_rows = train_df.count()
    test_rows = test_df.count()

    print("Train rows:", train_rows)
    print("Test rows :", test_rows)

    if train_rows == 0 or test_rows == 0:
        print("Skipping sector: train/test split failed")

        return [
            {
                "sector": sector_name,
                "model_name": "SKIPPED",
                "accuracy": None,
                "precision": None,
                "recall": None,
                "f1": None,
                "rows": sector_rows,
                "status": "skipped_empty_train_or_test",
            }
        ]

    label_indexer = StringIndexer(
        inputCol="target",
        outputCol="label",
        handleInvalid="skip",
    )

    assembler = VectorAssembler(
        inputCols=FEATURE_COLS,
        outputCol="raw_features",
        handleInvalid="skip",
    )

    scaler = StandardScaler(
        inputCol="raw_features",
        outputCol="features",
    )

    sector_safe_name = safe_name(sector_name)
    sector_model_dir = MODEL_DIR / sector_safe_name
    sector_model_dir.mkdir(parents=True, exist_ok=True)

    models = build_models()

    sector_results = []
    trained_models = {}

    for model_name, classifier in models.items():
        print("\n" + "-" * 70)
        print(f"Training {model_name} for sector: {sector_name}")
        print("-" * 70)

        pipeline = Pipeline(
            stages=[
                label_indexer,
                assembler,
                scaler,
                classifier,
            ]
        )

        try:
            model = pipeline.fit(train_df)
            predictions = model.transform(test_df)

            metrics = evaluate_model(model_name, predictions)

            result = {
                "sector": sector_name,
                "model_name": model_name,
                "accuracy": metrics["accuracy"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "rows": sector_rows,
                "status": "trained",
            }

            sector_results.append(result)
            trained_models[model_name] = model

            model_path = sector_model_dir / safe_name(model_name)
            safe_save_model(model, model_path, f"{sector_name} - {model_name}")

        except Exception as e:
            print("\n" + "!" * 70)
            print(f"ERROR training {model_name} for sector: {sector_name}")
            print("Reason:", str(e)[:700])
            print("This model will be skipped.")
            print("!" * 70)

            sector_results.append(
                {
                    "sector": sector_name,
                    "model_name": model_name,
                    "accuracy": None,
                    "precision": None,
                    "recall": None,
                    "f1": None,
                    "rows": sector_rows,
                    "status": f"error: {str(e)[:150]}",
                }
            )

    successful_results = [
        r for r in sector_results
        if r["status"] == "trained" and r["f1"] is not None
    ]

    if successful_results:
        best_result = sorted(
            successful_results,
            key=lambda x: x["f1"],
            reverse=True,
        )[0]

        best_model_name = best_result["model_name"]
        best_model = trained_models[best_model_name]

        best_model_path = sector_model_dir / "best_model"
        safe_save_model(best_model, best_model_path, f"{sector_name} - Best Model")

        print("\n" + "=" * 70)
        print(f"BEST MODEL FOR SECTOR: {sector_name}")
        print("=" * 70)
        print("Best Model:", best_model_name)
        print("Best F1-score:", best_result["f1"])
        print("Best model path:", best_model_path)

    else:
        print(f"No successful model for sector: {sector_name}")

    return sector_results


def train_sector_models():
    """
    Main function:
    - training data read
    - features create
    - sectors identify
    - har sector ke liye fast models train
    - report save
    """

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    spark = create_spark_session()

    try:
        print("Reading training data...")
        print("Input file:", INPUT_FILE)

        raw_df = (
            spark.read
            .option("header", True)
            .option("inferSchema", True)
            .csv(INPUT_FILE)
        )

        input_rows = raw_df.count()
        print("Input rows:", input_rows)

        required_cols = [
            "symbol",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "sector",
        ]

        missing_cols = [c for c in required_cols if c not in raw_df.columns]

        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        print("Creating ML features...")
        df = create_features(raw_df)

        feature_rows = df.count()
        print("Rows after feature engineering:", feature_rows)

        if feature_rows == 0:
            raise ValueError("No rows available after feature engineering.")

        print("\nAvailable sectors:")
        df.groupBy("sector").count().show(100, truncate=False)

        sectors = [
            row["sector"]
            for row in df.select("sector").distinct().collect()
            if row["sector"] is not None
        ]

        print("Total sectors found:", len(sectors))

        all_results = []

        for sector in sectors:
            sector_df = df.filter(col("sector") == sector)
            sector_results = train_one_sector(sector, sector_df)
            all_results.extend(sector_results)

        print("\n" + "=" * 90)
        print("FINAL SECTOR-WISE MODEL SUMMARY")
        print("=" * 90)

        for r in all_results:
            print(
                f"Sector: {r['sector']} | "
                f"Model: {r['model_name']} | "
                f"F1: {r['f1']} | "
                f"Status: {r['status']}"
            )

        import pandas as pd

        results_df = pd.DataFrame(all_results)
        results_df.to_csv(REPORT_FILE, index=False)

        print("\nSector model comparison report saved at:", REPORT_FILE)

    finally:
        spark.stop()


if __name__ == "__main__":
    train_sector_models()
