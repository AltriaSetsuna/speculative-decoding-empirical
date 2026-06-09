import json
from collections import defaultdict

# 引入 FastChat 的模板机制，保证 Prompt 100% 还原
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

def count_output_repetition(prefix_str: str, output_str: str, n: int) -> float:
    # 这里的计算逻辑保持不变，分母是 output，分子是全局出现 >1 的 ngram
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
                
    if output_total == 0:
        return 0.0
    return output_valid / output_total

def main(question_file: str, answer_file: str, model_name: str):
    questions = load_jsonl(question_file)
    answers = load_jsonl(answer_file)
    
    common_ids = set(questions.keys()).intersection(set(answers.keys()))
    print(f"Loaded {len(common_ids)} matching samples.")
    
    rates_t1 = {2: [], 3: [], 4: [], 5: []}
    rates_t2 = {2: [], 3: [], 4: [], 5: []}
    
    for qid in common_ids:
        q_turns = questions[qid]["turns"]
        a_turns = answers[qid]["choices"][0]["turns"]
        
        # ==========================================
        # 核心修改：使用 FastChat 原生模板还原真实上下文
        # ==========================================
        # 这里传入 model_name（如 "Qwen3-32B_vllm-0.12.0"），FastChat 会自动匹配模板
        conv = get_conversation_template(model_name)
        
        # --- 还原 Turn 1 ---
        conv.append_message(conv.roles[0], q_turns[0])
        conv.append_message(conv.roles[1], None)
        # get_prompt() 返回的就是模型推理时吃进去的真实字符串，包含所有 system prompt 和特殊符号
        prefix_t1 = conv.get_prompt() 
        output_t1 = a_turns[0]
        
        for n_val in [2, 3, 4, 5]:
            rates_t1[n_val].append(count_output_repetition(prefix_t1, output_t1, n_val))
            
        # --- 还原 Turn 2 ---
        if len(q_turns) > 1 and len(a_turns) > 1:
            # 更新上一轮的回答
            conv.update_last_message(output_t1)
            # 填入第二轮的问题
            conv.append_message(conv.roles[0], q_turns[1])
            conv.append_message(conv.roles[1], None)
            
            # 此时的 prompt 包含了：System + T1_Q + T1_A + T2_Q
            prefix_t2 = conv.get_prompt() 
            output_t2 = a_turns[1]
            
            for n_val in [2, 3, 4, 5]:
                rates_t2[n_val].append(count_output_repetition(prefix_t2, output_t2, n_val))

    # 打印结果逻辑与之前一致
    print("\n=== MT-Bench Dataset-Level Output Repetition Analysis (EGRR) ===")
    
    print("\n[Turn 1] (Fresh Generation without long history)")
    for n_val in [2, 3, 4, 5]:
        r = rates_t1[n_val]
        macro_avg = sum(r) / len(r) if r else 0
        print(f"  N = {n_val}: {macro_avg:.2%} (Macro-average)")
        
    print("\n[Turn 2] (Generation with context history)")
    for n_val in [2, 3, 4, 5]:
        r = rates_t2[n_val]
        macro_avg = sum(r) / len(r) if r else 0
        print(f"  N = {n_val}: {macro_avg:.2%} (Macro-average)")

if __name__ == "__main__":
    # 替换为你实际的文件路径
    QUESTION_FILE = "data/mt_bench/question.jsonl"
    ANSWER_FILE = "data/mt_bench/model_answer/Qwen3-32B_vllm-0.12.0.jsonl"
    # FastChat 会根据这个名字去寻找对应的 template (例如 qwen-7b-chat 会映射到 qwen 模板)
    # 如果你的名字没匹配上默认模板，可以硬编码传 "qwen" 或 "llama-3"
    MODEL_NAME = "Qwen3-32B_vllm-0.12.0" 
    
    main(QUESTION_FILE, ANSWER_FILE, MODEL_NAME)