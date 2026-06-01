import json
from datetime import datetime
from pathlib import Path
import yaml
from langchain_core.messages import HumanMessage, AIMessage # pyrefly: ignore [missing-import]


import os
import sys

def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.", file=sys.stderr)
        raise FileNotFoundError(f"Configuration file '{config_path}' not found.")

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error: Failed to parse '{config_path}': {e}", file=sys.stderr)
        raise e

    # Perform path validation warnings for local model paths
    model_paths = []
    if "ctransformers" in config and "model_path" in config["ctransformers"]:
        model_paths.append(config["ctransformers"]["model_path"].get("small"))
        model_paths.append(config["ctransformers"]["model_path"].get("large"))
    if "llava_model" in config:
        model_paths.append(config["llava_model"].get("llava_model_path"))
        model_paths.append(config["llava_model"].get("clip_model_path"))

    for p in model_paths:
        if p and not os.path.exists(p):
            print(f"Warning: Local model file not found at '{p}'. Please download it as specified in README.md.")

    return config


def save_chat_history_json(chat_history, file_path):
    with open(file_path, "w") as f:
        json_data = [message.dict() for message in chat_history]
        json.dump(json_data, f)


def load_chat_history_json(file_path):
    with open(file_path, "r") as f:
        json_data = json.load(f)
        messages = [HumanMessage(**message) if message["type"] == "human" else AIMessage(**message) for message in
                    json_data]
        return messages


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
