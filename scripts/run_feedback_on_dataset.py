#!/usr/bin/env python3
import sys
import os
import json
import argparse
from typing import List, Dict

# Ensure src is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from graphs.feedback_v2.orchestrator import feedback_graph_v2

def run_dataset(input_path: str, output_path: str):
    print(f"Processing dataset: {input_path}")
    
    results = []
    
    with open(input_path, 'r', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8') as f_out:
        
        for i, line in enumerate(f_in):
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                
                # Input validation
                if "code" not in record or "exercise_description" not in record:
                    print(f"Skipping line {i+1}: Missing 'code' or 'exercise_description'.")
                    continue
                
                # Prepare graph input
                graph_input = {
                    "code": record["code"],
                    "exercise_description": record["exercise_description"],
                    "previous_feedback": record.get("previous_feedback", []),
                    "results": [],
                    "retry_counts": {},
                    "aggregated_feedback": {}
                }
                
                # Run Graph
                print(f"Running graph for record {i+1}...")
                graph_output = feedback_graph_v2.invoke(graph_input)
                
                # Extract result
                record["feedback_result"] = graph_output.get("aggregated_feedback", {})
                
                # Write to output immediately (streaming)
                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                f_out.flush()
                
            except json.JSONDecodeError:
                print(f"Skipping line {i+1}: Invalid JSON.")
            except Exception as e:
                print(f"Error processing line {i+1}: {str(e)}")
                # Write error record?
                record["error"] = str(e)
                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Done. Results saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Feedback Graph V2 on a JSONL dataset.")
    parser.add_argument("input_file", help="Path to input JSONL file.")
    parser.add_argument("output_file", help="Path to save output JSONL file.")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        sys.exit(1)
        
    run_dataset(args.input_file, args.output_file)
