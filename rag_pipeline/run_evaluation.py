from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag_pipeline.evaluation import run_benchmark

if __name__ == "__main__":
    result = run_benchmark(5)
    print(result["run_id"])