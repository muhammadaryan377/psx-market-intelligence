#!/usr/bin/env python3
"""
PySpark Stream Processor Runner
Runs stream_processor without needing spark-submit command
"""
import subprocess
import sys
import os

def ensure_pyspark_installed():
    """Install PySpark if not already present"""
    try:
        import pyspark
        print(f"✓ PySpark {pyspark.__version__} already installed")
        return
    except ImportError:
        print("Installing PySpark...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyspark>=4.1.1"])

if __name__ == "__main__":
    # Install PySpark first
    ensure_pyspark_installed()
    
    # Now import and run
    from spark_layer.stream_processor import main
    
    print("\n" + "="*60)
    print("Starting PSX Intelligence System - Spark Stream Processor")
    print("="*60 + "\n")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStream processor stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
