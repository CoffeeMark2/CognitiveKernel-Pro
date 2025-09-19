#!/bin/bash
export OPENAI_API_KEY="sk-2e8a1b3dcd904a6faa6f06e087c3e9de"
export OPENAI_ENDPOINT="https://dashscope.aliyuncs.com/compatible-mode/v1"
export PYTHONPATH=/root/ck
export SEARCH_BACKEND="DuckDuckGo"
# Assume we have set up a vllm model server and a web-browser server (currently these are active: WEB_IP
WEB_IP=localhost:3001  # web-browser server
# LLM_URL=http://xx.xx.xx.xx:8080/v1/chat/completions  # vllm model server
#LLM_URL=gpt:gpt-4.1  # using gpt
#VLM_URL=gpt:gpt-4.1  # using gpt
#LLM_URL=claude:  # using claude
#VLM_URL=claude:  # using claude
# run simple test
MAIN_ARGS="{'web_agent': {'model': {'call_target': '${LLM_URL}'}, 'model_multimodal': {'call_target': '${VLM_URL}'}, 'web_env_kwargs': {'web_ip': '${WEB_IP}'}}, 'file_agent': {'model': {'call_target': '${LLM_URL}'}, 'model_multimodal': {'call_target': '${VLM_URL}'}}, 'model': {'call_target': '${LLM_URL}'}}"
# use "NO_NULL_STDIN=1" for easier debugging
# you can also remove `--input` field to directly input your task from stdin
# you can also remove `-mpdb` flag to run the program directly instead of in debugging mode

TIMESTAMP=$(date +%Y%m%d)

# 执行命令
# 1> >(...) 将 stdout 传递给 tee 进程，该进程同时写入文件和屏幕
# 2> >(...) 将 stderr 传递给另一个 tee 进程，该进程也同时写入文件和屏幕
# NO_NULL_STDIN=1 python3 -u -m ck_pro.ck_main.main --input ck_pro/ck_main/_test/simple_test.jsonl --output ck_pro/ck_main/_test/simple_test.output.jsonl |& tee _log_simple_test
# less -R _log_simple_test  # use 'less -R' to see the colored outputs

NO_NULL_STDIN=1 python3 -u -m ck_pro.ck_main.main \
  --input gaia/simple_test.jsonl \
  --output gaia/simple_test_res_${TIMESTAMP}.jsonl \
  1> >(tee "gaia/log_${TIMESTAMP}.log") \
  2> >(tee "gaia/err_${TIMESTAMP}.err" >&2)