input_jsonl_file = 'result/gaia_20250910.jsonl'


import json
import re
import string
import warnings
import shutil
import os
import datetime
import pandas as pd


def normalize_number_str(number_str: str) -> float:
    for char in ["$", "%", ","]:
        number_str = number_str.replace(char, "")
    try:
        return float(number_str)
    except ValueError:
        print(f"String {number_str} cannot be normalized to number str.")
        return float("inf")


def split_string(
    s: str,
    char_list: list[str] = [",", ";"],
) -> list[str]:
    pattern = f"[{''.join(char_list)}]"
    return re.split(pattern, s)


def question_scorer(
    model_answer: str,
    ground_truth: str,
) -> bool:
    def is_float(element: any) -> bool:
        try:
            float(element)
            return True
        except ValueError:
            return False

    if is_float(ground_truth):
        # print(f"Evaluating {model_answer} as a number.")
        normalized_answer = normalize_number_str(model_answer)
        return normalized_answer == float(ground_truth)

    elif any(char in ground_truth for char in [",", ";"]):
        # print(f"Evaluating {model_answer} as a comma separated list.")

        gt_elems = split_string(ground_truth)
        ma_elems = split_string(model_answer)

        if len(gt_elems) != len(ma_elems):
            warnings.warn(
                "Answer lists have different lengths, returning False.", UserWarning
            )
            return False

        comparisons = []
        for ma_elem, gt_elem in zip(ma_elems, gt_elems):
            if is_float(gt_elem):
                normalized_ma_elem = normalize_number_str(ma_elem)
                comparisons.append(normalized_ma_elem == float(gt_elem))
            else:
                comparisons.append(
                    normalize_str(ma_elem, remove_punct=False)
                    == normalize_str(gt_elem, remove_punct=False)
                )
        return all(comparisons)

    else:
        # print(f"Evaluating {model_answer} as a string.")
        return normalize_str(model_answer) == normalize_str(ground_truth)


def normalize_str(input_str, remove_punct=True) -> str:

    no_spaces = re.sub(r"\s", "", input_str)

    if remove_punct:
        translator = str.maketrans("", "", string.punctuation)
        return no_spaces.lower().translate(translator)
    else:
        return no_spaces.lower()



def process_and_evaluate_jsonl_combined(
    file_path, 
    output_dir='result/output_jsons', 
    results_filename='result/evaluation_results.csv',
    backup_dir_name='backup'
):
    """
    拆分、评估JSONL文件，用成功案例覆盖原文件，并生成统计报告。

    新功能:
    1. 在处理前，将原始输入文件备份到一个带时间戳的子目录中。
    2. 处理完成后，用仅包含成功案例的内容覆盖原始的JSONL文件。

    原有功能:
    1. 将JSONL文件按行拆分成独立的JSON文件（跳过已存在的文件）。
    2. 使用 question_scorer 评估每行的 'pred' 和 'gold' 值。
    3. 使用 pandas 为所有处理过的行创建一个详细的CSV报告。
    4. 计算并输出总成功率及各项操作的总结。

    参数:
    file_path (str): 输入的JSONL文件路径。
    output_dir (str): 拆分后JSON文件的存放目录。
    results_filename (str): 评估结果报告（CSV文件）的文件名。
    backup_dir_name (str): 用于存放备份文件的文件夹名称。
    """
    # 1. 检查和准备环境
    if not os.path.exists(file_path):
        print(f"错误：找不到输入文件 '{file_path}'")
        return

    # --- 新增功能: 备份原始文件 ---
    try:
        input_dir = os.path.dirname(file_path) or '.'
        backup_dir = os.path.join(input_dir, backup_dir_name)
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(file_path)
        backup_path = os.path.join(backup_dir, f"{timestamp}_{base_name}")
        
        shutil.copy2(file_path, backup_path)
        print(f"文件已成功备份至: '{backup_path}'")
    except Exception as e:
        print(f"错误：备份文件失败: {e}")
        return # 如果备份失败，则停止处理

    if not os.path.exists(output_dir):
        print(f"创建输出目录: '{output_dir}'")
        os.makedirs(output_dir)

    print(f"开始处理文件: '{file_path}'")
    
    # 2. 初始化变量
    results_data = []
    new_files_created = 0
    files_skipped = 0
    total_lines = 0
    temp_success_file = file_path + '.tmp'

    # 3. 主处理循环
    try:
        with open(file_path, 'r', encoding='utf-8') as f_in, \
             open(temp_success_file, 'w', encoding='utf-8') as f_success_out:
            
            for line_num, line in enumerate(f_in, 1):
                total_lines = line_num
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                
                row_result = {'ID': f"line_{line_num}", 'Gold': None, 'Prediction': None, 'Result': 'PROCESSING_ERROR'}

                try:
                    data = json.loads(stripped_line)
                    file_id = data.get('id', f"line_{line_num}")
                    row_result['ID'] = str(file_id)

                    eval_data = data.get('eval', {})
                    gold_value = eval_data.get('gold')
                    pred_value = eval_data.get('pred')
                    
                    row_result['Gold'] = gold_value
                    row_result['Prediction'] = pred_value
                    
                    is_success = question_scorer(pred_value, gold_value)
                    
                    if is_success:
                        row_result['Result'] = "SUCCESS"
                        f_success_out.write(stripped_line + '\n')
                    else:
                        row_result['Result'] = "FAILURE"

                    output_filename = os.path.join(output_dir, f"{row_result['ID']}.json")
                    # if os.path.exists(output_filename):
                    #     files_skipped += 1
                    # else:
                    #     with open(output_filename, 'w', encoding='utf-8') as out_f:
                    #         json.dump(data, out_f, ensure_ascii=False, indent=4)
                    #     new_files_created += 1
                    with open(output_filename, 'w', encoding='utf-8') as out_f:
                        json.dump(data, out_f, ensure_ascii=False, indent=4)
                        new_files_created += 1

                except json.JSONDecodeError:
                    print(f"警告：第 {line_num} 行不是有效的JSON格式，已跳过。")
                    row_result['Result'] = 'INVALID_JSON'
                except Exception as e:
                    print(f"处理第 {line_num} 行时发生未知错误: {e}")
                
                results_data.append(row_result)
        
        # --- 新增功能: 用临时文件安全地替换原文件 ---
        os.replace(temp_success_file, file_path)

        # 4. 生成报告和总结
        if not results_data:
            print("警告：未处理任何数据。")
            return

        results_df = pd.DataFrame(results_data)
        results_df.to_csv(results_filename, index=False, encoding='utf-8')

        total_tasks = len(results_df)
        successful_tasks = (results_df['Result'] == 'SUCCESS').sum()
        success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0

        print("\n" + "-"*20 + " 处理与评估完成! " + "-"*20)
        print("\n文件拆分摘要:")
        print(f"  - 新增文件: {new_files_created}")
        print(f"  - 因已存在而跳过: {files_skipped}")
        print(f"  - 拆分文件保存在 '{output_dir}' 目录下。")
        print("\n任务评估摘要:")
        print(f"  - 总共处理行数: {total_lines}")
        print(f"  - 成功任务数: {successful_tasks}")
        print(f"  - 最终成功率: {success_rate:.2f}%")
        print(f"  - 原文件 '{os.path.basename(file_path)}' 已更新，仅保留成功案例。")
        print(f"  - 详细评估报告已保存至 '{results_filename}'。")
        print("-"*60)
        return success_rate

    except Exception as e:
        print(f"处理过程中发生严重错误: {e}")
        # 如果出错，确保删除临时文件
        if os.path.exists(temp_success_file):
            os.remove(temp_success_file)
        return 0.0

if __name__ == "__main__":
    # 示例用法
    sample_filename = input_jsonl_file  # 替换为你的JSONL文件路径    
    process_and_evaluate_jsonl_combined(sample_filename)