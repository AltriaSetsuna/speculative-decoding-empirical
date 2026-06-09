import json
from collections import defaultdict

# 引入 FastChat 的模板机制
from fastchat.model.model_adapter import get_conversation_template

def load_jsonl(file_path):
    data_dict = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            data_dict[item["question_id"]] = item
    return data_dict

def count_valid_and_total_ngrams(prefix_str: str, output_str: str, n: int) -> tuple[int, int]:
    """
    计算某一轮次中的：有效重复 N-gram 数量(分子) 和 总 Output N-gram 数量(分母)
    """
    prefix_words = prefix_str.split()
    output_words = output_str.split()
    full_words = prefix_words + output_words
    
    global_m = defaultdict(int)
    if len(full_words) >= n:
        for i in range(len(full_words) - n + 1):
            ngram_key = " ".join(full_words[i:i+n])
            global_m[ngram_key] += 1
            
    output_total = 0
    output_valid = 0
    if len(output_words) >= n:
        for i in range(len(output_words) - n + 1):
            ngram_key = " ".join(output_words[i:i+n])
            output_total += 1
            if global_m[ngram_key] > 1:
                output_valid += 1
                
    return output_valid, output_total

def main(question_file: str, answer_file: str, model_name: str):
    questions = load_jsonl(question_file)
    answers = load_jsonl(answer_file)
    
    common_ids = set(questions.keys()).intersection(set(answers.keys()))
    print(f"Loaded {len(common_ids)} matching samples.")
    
    # 存储每个样本的合并重复率
    rates_combined = {2: [], 3: [], 4: [], 5: []}
    
    for qid in common_ids:
        q_turns = questions[qid]["turns"]
        a_turns = answers[qid]["choices"][0]["turns"]
        
        conv = get_conversation_template(model_name)
        
        # --- 提取 Turn 1 ---
        conv.append_message(conv.roles[0], q_turns[0])
        conv.append_message(conv.roles[1], None)
        prefix_t1 = conv.get_prompt() 
        output_t1 = a_turns[0]
        
        # --- 提取 Turn 2 ---
        has_turn2 = len(q_turns) > 1 and len(a_turns) > 1
        prefix_t2 = ""
        output_t2 = ""
        if has_turn2:
            conv.update_last_message(output_t1)
            conv.append_message(conv.roles[0], q_turns[1])
            conv.append_message(conv.roles[1], None)
            prefix_t2 = conv.get_prompt() 
            output_t2 = a_turns[1]
            
        # --- 合并计算每个 N 值的全局重复率 ---
        for n_val in [2, 3, 4, 5]:
            # 获取第一轮的分子与分母
            valid_t1, total_t1 = count_valid_and_total_ngrams(prefix_t1, output_t1, n=n_val)
            
            # 获取第二轮的分子与分母
            valid_t2, total_t2 = 0, 0
            if has_turn2:
                valid_t2, total_t2 = count_valid_and_total_ngrams(prefix_t2, output_t2, n=n_val)
                
            # 将多轮的分子分母进行相加
            sample_valid = valid_t1 + valid_t2
            sample_total = total_t1 + total_t2
            
            if sample_total == 0:
                rates_combined[n_val].append(0.0)
            else:
                rates_combined[n_val].append(sample_valid / sample_total)

    # 打印最终的宏平均结果
    print("\n=== MT-Bench Dataset-Level Output Repetition Analysis (Session-Combined EGRR) ===")
    print("This metric considers the entire multi-turn conversation as a single evaluation unit.\n")
    
    for n_val in [2, 3, 4, 5]:
        r = rates_combined[n_val]
        macro_avg = sum(r) / len(r) if r else 0
        print(f"  N = {n_val}: {macro_avg:.2%} (Macro-average across {len(common_ids)} multi-turn sessions)")

if __name__ == "__main__":
    # 请替换为你的实际文件路径
    QUESTION_FILE = "data/mt_bench/question.jsonl"
    ANSWER_FILE = "data/mt_bench/model_answer/Qwen3-32B_vllm-0.12.0.jsonl"
    MODEL_NAME = "Qwen3-32B_vllm-0.12.0" 
    
    main(QUESTION_FILE, ANSWER_FILE, MODEL_NAME)