import json
import os

def calculate_turn_lengths(input_file):
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 找不到文件 '{input_file}'")
        return

    print(f"{'Question ID':<15} | {'Total Length (Turn 0 + Turn 1)':<30}")
    print("-" * 50)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # 提取 question_id
                    q_id = data.get('question_id', 'Unknown')
                    
                    # 获取 choices 列表
                    choices = data.get('choices', [])
                    
                    # 确保 choices 不为空且包含 turns
                    if choices and isinstance(choices, list) and 'turns' in choices[0]:
                        turns = choices[0]['turns']
                        
                        # 确保 turns 至少有两个元素
                        if isinstance(turns, list) and len(turns) >= 2:
                            # 计算 turns[0] + turns[1] 的长度
                            length_0 = len(turns[0])
                            length_1 = len(turns[1])
                            total_len = length_0 + length_1
                            
                            print(f"{str(q_id):<15} | {total_len:<30}")
                        else:
                            print(f"{str(q_id):<15} | {'Skipped (turns < 2)':<30}")
                    else:
                        print(f"{str(q_id):<15} | {'Skipped (invalid format)':<30}")

                except json.JSONDecodeError:
                    print(f"行 {line_number}: JSON 解析错误")
                    
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    # 在这里修改你的文件名
    file_name = '/home/anonymous/project/FastChat/fastchat/llm_judge/data/mt_bench/model_answer/Qwen3-32B_vllm-0.12.0.jsonl' 
    calculate_turn_lengths(file_name)