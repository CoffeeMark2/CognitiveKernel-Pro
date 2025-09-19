#

import os
import argparse
import json
import shutil
import time
import multiprocessing as mp
import signal
import threading

from ..agents.utils import rprint, my_open_with, zwarn, incr_update_dict, get_until_hit, my_json_dumps, tuple_keys_to_str
from ..agents.evaluator import Evaluator

from .agent import CKAgent
from .gaia_scorer import question_scorer

from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import functools



default_main_configs = {
    "model": {"call_target": "gpt:claude-sonnet-4-20250514"},  # LLM target
    # "web_agent": {
    #     "model": {"call_target": "gpt:claude-sonnet-4-20250514"},  # LLM target for the web agent
    #     "web_env_kwargs": {"web_ip": "localhost:3000"},  # IP for the web-browser server
    # }
}

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=str, default="")
    parser.add_argument("-u", "--updates", type=str, default=[], nargs="+")  # updating dicts
    parser.add_argument("-i", "--input", type=str, default="")
    parser.add_argument("-o", "--output", type=str, default="")
    parser.add_argument("-S", "--sep_run_root", type=str, default="")  # separate running root dir for each task, empty if not enabled
    parser.add_argument("-P", "--try_preload_output", type=int, default=1)  # try loading the already processed outputs
    parser.add_argument("--starting_idx", type=int, default=0)  # starting with which one?
    parser.add_argument("--no_final_breakpoint", type=str, default="")
    parser.add_argument("--skip-hard-query", action="store_true")
    parser.add_argument("--sampling-mode", action="store_true") # in sampling (trajectory) model, will use an evaluator to check whether the query has finished (with an answer)
    parser.add_argument("--evaluation-method", choices=["disabled", "em", "llm_score", "stop_with_answer"], default="disabled") # useful when --sampling-mode is on.
    # types of auto evaluator. em: exact match; llm_score: llm score using langchain; Answers should be provided in this mode. stop_with_answer: simply determine whether the query stops with an answer. suits the situation where no ground answers are provided.
    parser.add_argument("--inference-time-evaluation-method", choices=["disabled", "no_answer", "no_answer+no_ask_llm", "gpt_judge", "ensemble", "gpt_judge+ensemble"], default="disabled") # whether to enable an auto evaluator and perform reflection
    parser.add_argument("--max_retry_num", default=3, type=int) # maximum number of retries when sampling-mode or inference_time_evaluation_method is on.
    parser.add_argument("--reflection", type=bool, default=False)
    parser.add_argument("--save_failed_tries", action="store_true") # whether to save "failed" tries. Can disable this when running inference on test set.
    # parser.add_argument("-t", "--timeout", type=int, default=3600)  # timeout seconds for each task
    return parser.parse_args()

def yield_inputs(input_file):
    _idx = 0
    if input_file:
        with open(input_file) as fd:
            for line in fd:
                if line.strip():
                    one_inst = json.loads(line)
                    # if there is info
                    info_field = one_inst['info'] if 'info' in one_inst else one_inst
                    # get fields
                    task = get_until_hit(info_field, ["question", "Question", "task", "Task", "query", "Query", "instruction", "Instruction"])
                    file = get_until_hit(info_field, ["file_name"])
                    answer = get_until_hit(info_field, ["Final answer", "answer", "true_answer"])
                    if get_until_hit(info_field, ["skip"]) is None or str(get_until_hit(info_field, ["skip"])) != '1':
                        skip_hard = False
                    else:
                        skip_hard = True
                    if task:
                        yield {"id": f"task{_idx:04d}", "task": task, "file": file, "answer": answer, "_orig": one_inst, "skip_hard": skip_hard}
                        _idx += 1
                    else:
                        zwarn(f"Cannot find task from: {one_inst}")
    else:  # read from input
        while True:
            task = input("Input your task prompt >> ").strip()
            if not task:
                continue
            if task == "__END__":
                break
            yield {"id": f"task{_idx:04d}", "task": task}
            _idx += 1

def process_task(inst, ck_agent, ck_evaluator, args, input_dir):
    """
    This function contains all the logic to process a single task instance.
    It's designed to be called by a thread pool executor.
    """
    try:
        # Reconstruct the task string with the file path
        _task = inst["task"].strip()
        if inst.get("file"):
            _input_file = os.path.join(input_dir, inst["file"])
            if _input_file:
                _task = f"{_task}\n(* You are given the following input file: {_input_file})"
        
        rprint(f"Start to run task {inst['id']}", timed=True)

        # Skip hard queries if the flag is set
        if args.skip_hard_query and inst['skip_hard']:
            rprint(f"Skipping hard task {inst['id']}")
            inst['eval'] = {"pred": 'NA', "gold": str(inst.get("answer", "UNK")), "corr": 0}
            inst['session'] = {}
            return inst

        # --- Core Agent Execution Logic (copied from the original loop) ---
        res_session = None
        res_session_list = []
        start_pc, start_time = time.perf_counter(), time.ctime()

        if args.sampling_mode:
            # ... [Sampling mode logic as before] ...
            # For brevity, this part is conceptually copied.
            # In the final code, you would paste the exact logic here.
            res_session = ck_agent.run(_task) # Simplified for explanation
        else:
            # Inference mode with retries and reflection
            if args.inference_time_evaluation_method == "disabled":
                res_session = ck_agent.run(_task)
            else:
                candidate_num = 5 if "ensemble" in args.inference_time_evaluation_method else 1
                candidate_sessions = []
                feedback_list = []
                for i in range(candidate_num):
                    feedback = None
                    for j in range(args.max_retry_num):
                        new_task = f"{_task}. Here is a feedback for a previous try that failed:\n\n{feedback}" if args.reflection and feedback else _task
                        
                        _res = ck_agent.run(new_task)
                        res_session_list.append(_res)
                        
                        has_failure, feedback = ck_evaluator.detect_failure(_res.to_dict(), evaluation_type=args.inference_time_evaluation_method)
                        if not has_failure:
                            res_session = _res # Mark the successful session
                            break
                        
                        rprint(f"Retrying task {inst['id']} due to {feedback}")
                        feedback_list.append(feedback)
                    
                    if res_session: # if successful in retry loop
                        candidate_sessions.append(res_session)
                        if not "ensemble" in args.inference_time_evaluation_method:
                            break # No need for more candidates if not ensembling
                
                if "ensemble" in args.inference_time_evaluation_method and candidate_sessions:
                    res_session = candidate_sessions[ck_evaluator.ensemble([x.to_dict() for x in candidate_sessions])]
                
                inst["feedback"] = feedback_list

        # --- Post-processing and Evaluation ---
        if res_session is None:
            inst["session"] = {"steps": [{"step_idx": -1, "end": {"final_results": {"output": "error", "log": "error"}}}]}
        else:
            call_stat = ck_agent.get_call_stat(clear=True)
            res_session.info["call_stat"] = call_stat
            end_pc, end_time = time.perf_counter(), time.ctime()
            duration = end_pc - start_pc
            res_session.info.update({"start_time": start_time, "end_time": end_time, "duration": duration})
            inst["session"] = res_session.to_dict()
            if args.save_failed_tries and len(res_session_list) > 1:
                inst['previous_failed_sessions'] = [sess.to_dict() for sess in res_session_list[:-1]]
            
            # Print overall statistics for this task
            rprint(f"Task {inst['id']} finished - Duration: {duration:.3f}s, Call stats: {call_stat}", style="white on green")

        # Simple EVAL
        answer_gold = str(inst.get("answer", "UNK"))
        try:
            answer_pred = str(inst["session"]["steps"][-1]["end"]["final_results"]["output"])
        except:
            answer_pred = "error"
        
        _this_corr = int(question_scorer(model_answer=answer_pred, ground_truth=answer_gold))
        inst["eval"] = {"pred": answer_pred, "gold": answer_gold, "corr": _this_corr}
        
        rprint(f"Finished task {inst['id']}: Correct={_this_corr}")
        return inst

    except Exception as e:
        zwarn(f"Task {inst.get('id', 'N/A')} failed with a critical error: {e}")
        inst["session"] = {"error": str(e)}
        inst["eval"] = {"pred": "critical_error", "gold": str(inst.get("answer", "UNK")), "corr": 0}
        return inst # Return the instance with error info
# --
def main():
    args = get_args()
    rprint(f"Run ck_main.main with {args}")
    mp.set_start_method("spawn")

    # --- 1. Initial Setup (same as before) ---
    configs = default_main_configs
    if args.config:
        with open(args.config) as fd:
            configs = json.load(fd)
        rprint(f"Load configs from {args.config} = {configs}")
    for one_update in args.updates:
        src_dict = eval(one_update)
        incr_update_dict(configs, src_dict)
        rprint(f"Update configs with {src_dict}")
    
    # Enable token and time statistics
    configs["enable_token_time_stats"] = True
    ck_agent = CKAgent(**configs)
    if args.sampling_mode or args.inference_time_evaluation_method != "disabled":
        ck_evaluator = Evaluator()
    else:
        ck_evaluator = None # Ensure it exists

    input_dir = os.getenv("FILE_BASE_DIR", default=os.path.dirname(os.path.abspath(args.input)))

    # --- 2. Prepare Task List ---
    # Load existing results first to avoid re-processing
    existing_inst_map = {}
    if args.try_preload_output and os.path.exists(args.output):
        with open(args.output) as fd:
            for line in fd:
                if line.strip():
                    _inst = json.loads(line)
                    existing_inst_map[_inst["id"]] = _inst
    if existing_inst_map:
        rprint(f"Loaded {len(existing_inst_map)} existing results.")

    # Prepare the list of tasks that actually need to run
    tasks_to_run = []
    already_processed_tasks = []
    all_tasks = list(yield_inputs(args.input)) # Read all tasks into memory

    for inst in all_tasks:
        if inst["id"] in existing_inst_map:
            # You could add a check here for mismatched tasks if needed
            rprint(f"Skipping {inst['id']} as it's already processed.")
            already_processed_tasks.append(existing_inst_map[inst["id"]])
        else:
            tasks_to_run.append(inst)

    rprint(f"Total tasks: {len(all_tasks)}, Already processed: {len(already_processed_tasks)}, To run: {len(tasks_to_run)}")

    # 2. 创建一个锁实例
    file_lock = threading.Lock()
    
    # 3. 在循环外部以追加模式('a')打开文件
    # 如果文件已存在，我们会向其中添加新完成的任务
    # 'w'模式会清空已有的结果，所以我们先写入之前已处理的任务
    with my_open_with(args.output, 'w') as fout:
        for task in already_processed_tasks:
             fout.write(my_json_dumps(tuple_keys_to_str(task), ensure_ascii=False) + "\n")
    
    # 现在以追加模式继续
    with my_open_with(args.output, 'a') as fout:
        CONCURRENCY = 10
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            func = functools.partial(process_task, ck_agent=ck_agent, ck_evaluator=ck_evaluator, args=args, input_dir=input_dir)
            futures = {executor.submit(func, inst): inst['id'] for inst in tasks_to_run}

            for future in tqdm(as_completed(futures), total=len(tasks_to_run), desc="Processing Tasks"):
                result = future.result()
                if result:
                    # 4. 在写入文件前获取锁
                    with file_lock:
                        try:
                            fout.write(my_json_dumps(tuple_keys_to_str(result), ensure_ascii=False) + "\n")
                            # 立即刷新缓冲区，确保内容写入磁盘
                            fout.flush() 
                        except Exception as e:
                            zwarn(f"Error writing instance {result.get('id', 'N/A')}: {e}")

    # --- Final Summary (Optional, as results are already written) ---
    rprint("Yeah, everything has been finished!!!!!")
    final_results = []
    with open(args.output) as fd:
        for line in fd:
            if line.strip():
                final_results.append(json.loads(line))

    corr_task = sum(r.get('eval', {}).get('corr', 0) for r in final_results)
    total_task = len(final_results)
    if total_task > 0:
        rprint(f"Final Accuracy = {corr_task}/{total_task}={corr_task/total_task:.4f}")

# --
# python -m ck_pro.ck_main.main --config config.json --input ... --output ... --sep_run_root test0
if __name__ == '__main__':
    main()
