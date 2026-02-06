import os
import dashscope
from http import HTTPStatus
from dotenv import load_dotenv

load_dotenv()

def alibaba_rerank(query: str, documents: list[str]):
    """使用阿里百炼 gte-rerank-v2 进行精准排序"""
    responses = dashscope.TextReRank.call(
        model="gte-rerank-v2",
        query=query,
        documents=documents,
        top_n=3,
        api_key=os.getenv("DASHSCOPE_API_KEY")
    )
    if responses.status_code == HTTPStatus.OK:
        return responses.output.results
    return None