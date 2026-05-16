import json
from datetime import datetime
import yaml
<<<<<<< HEAD
from langchain_core.messages import HumanMessage, AIMessage
=======
from langchain_core.messages import HumanMessage, AIMessage # pyrefly: ignore [missing-import]
>>>>>>> cf049224449266d41007d6fac7ce8805e96a22cb


def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


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
<<<<<<< HEAD
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")
=======
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
>>>>>>> cf049224449266d41007d6fac7ce8805e96a22cb
