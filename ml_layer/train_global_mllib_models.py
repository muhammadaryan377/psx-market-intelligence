from pathlib import Path
import re
import sys
import os

from pyspark.sql import SparkSession  # type: ignore
from pyspark.sql.functions import col, unix_timestamp, to_timestamp  # type: ignore

from pyspark.ml import Pipeline  # type: ignore
from pyspark.ml.feature import StringIndexer, VectorAssembler, StandardScaler  # type: ignore
from pyspark.ml.classification import ( # type: ignore
    LogisticRegression,
    RandomForestClassifier,
)  # type: ignore
from pyspark.ml.evaluation import MulticlassClassificationEvaluator  # type: ignore


# ---------------------------------------------------------
# Windows Hadoop setup
# ---------------------------------------------------------
# Agar C:\hadoop\bin mein winutils.exe aur hadoop.dll hain,
# to Spark local save/write issues reduce ho jate hain.
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
INPUT_FILE = r"data/processed/ml_training_prices.csv"
REPORT_FILE = Path("data/reports/global_model_comparison.csv")
MODEL_DIR = Path("ml_layer/models/global")


def create_spark_session():
    """
    Spark session create karta hai.
    Windows local filesystem ke liye kuch configs add ki hain.
    """

    Path("C:/tmp/spark-warehouse").mkdir(parents=True, exist_ok=True)

    spark = (
        SparkSession.builder
        .appName("PSX_Global_MLlib_Model_Training")
        .master("local[*]")
        .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
        .config("spark.sql.warehouse.dir", "file:///C:/tmp/spark-warehouse")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")
    return spark


def safe_name(name: str) -> str:
    """
    Model name ko folder-safe banata hai.
    Example:
    'Logistic Regression' -> 'logistic_regression'
    """

    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name


def time_based_split(df):
    """
    Time-series data ke liye random split sahi nahi hota.
    Isliye old 80% dates training ke liye,
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
    Model ki performance metrics calculate karta hai.
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
        "model_name": model_name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def safe_save_model(model, save_path: Path, model_name: str) -> bool:
    """
    Spark ML model save karta hai.
    Windows/Hadoop issue aaye to script crash nahi hogi.
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

    Slow third model remove kiya gaya hai kyunki multi-class wrapper local
    Windows setup par bohot zyada time le sakta hai.
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


def train_global_models():
    """
    Main function:
    - data read
    - features create
    - train/test split
    - 3 models train
    - metrics compare
    - best model select
    - report save
    """

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    spark = create_spark_session()

    try:
        print("Reading training data...")
        print("Input file path:", INPUT_FILE)
        print("Replay data is not used for training.")

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

        print("\nTarget distribution:")
        df.groupBy("target").count().show()

        train_df, test_df = time_based_split(df)

        train_rows = train_df.count()
        test_rows = test_df.count()

        print("Train rows:", train_rows)
        print("Test rows :", test_rows)

        if train_rows == 0 or test_rows == 0:
            raise ValueError("Train/test split failed. Train or test data is empty.")

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

        models = build_models()

        results = []
        trained_models = {}

        for model_name, classifier in models.items():
            print("\n" + "-" * 70)
            print(f"Training {model_name}...")
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

                result = evaluate_model(model_name, predictions)

                results.append(result)
                trained_models[model_name] = model

                save_path = MODEL_DIR / safe_name(model_name)
                safe_save_model(model, save_path, model_name)

            except Exception as e:
                print("\n" + "!" * 70)
                print(f"ERROR while training {model_name}")
                print("Reason:", str(e)[:700])
                print("This model will be skipped.")
                print("!" * 70)

        if not results:
            raise ValueError("No model trained successfully.")

        best_result = sorted(results, key=lambda x: x["f1"], reverse=True)[0]
        best_model_name = best_result["model_name"]
        best_model = trained_models[best_model_name]

        best_model_path = MODEL_DIR / "best_model"
        safe_save_model(best_model, best_model_path, "Best Global Model")

        print("\n" + "=" * 70)
        print("FINAL GLOBAL MODEL COMPARISON")
        print("=" * 70)

        for r in results:
            print(
                f"{r['model_name']} | "
                f"Accuracy: {r['accuracy']:.4f} | "
                f"Precision: {r['precision']:.4f} | "
                f"Recall: {r['recall']:.4f} | "
                f"F1: {r['f1']:.4f}"
            )

        print("\nBest model by F1-score:", best_model_name)
        print("Best F1-score:", best_result["f1"])
        print("Best model path:", best_model_path)

        import pandas as pd

        results_df = pd.DataFrame(results)
        results_df.to_csv(REPORT_FILE, index=False)

        print("\nComparison report saved at:", REPORT_FILE)

    finally:
        spark.stop()


if __name__ == "__main__":
    train_global_models()
