import argparse
import json

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--globals", type=str, default="{}")
    args = parser.parse_args()
    global_config = json.loads(args.globals)
    return args.port, global_config
