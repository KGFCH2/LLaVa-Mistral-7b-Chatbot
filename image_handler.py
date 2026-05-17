import streamlit as st  # pyrefly: ignore [missing-import]
from llama_cpp import Llama # pyrefly: ignore [missing-import]
from llama_cpp.llama_chat_format import MoondreamChatHandler # pyrefly: ignore [missing-import]
from utils import load_config
import base64

config = load_config()


def convert_bytes_to_base64(image_bytes):
    return base64.b64encode(image_bytes).decode("utf-8")


def handle_image(image_bytes, user_input):
    # Using moondream model for image description via llama-cpp-python
    # Ensure you have the moondream model in your models folder and path updated in config.yaml
    chat_handler = MoondreamChatHandler(
        clip_model_path=config["moondream"]["clip_model_path"]
    )

    llm = Llama(
        model_path=config["moondream"]["model_path"],
        chat_handler=chat_handler,
        n_ctx=2048,  # n_ctx should be sufficient for the image and text
    )

    image_base64 = convert_bytes_to_base64(image_bytes)

    response = llm.create_chat_completion(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_input},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ],
            }
        ]
    )

    return response["choices"][0]["message"]["content"]