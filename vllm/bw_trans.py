import pandas as pd

def process_log_file(file_path, output_path, gpu_nums):
    drama_values = []
    
    # 1. 读取文件并提取所有 GPU 的 drama 值
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 匹配以 "GPU" 开头的行
                if line.startswith('GPU'):
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            # 取最后一个元素作为数值
                            val = float(parts[-1])
                            drama_values.append(val)
                        except ValueError:
                            continue
    except FileNotFoundError:
        print(f"错误: 找不到文件 {file_path}")
        return

    if not drama_values:
        print("未找到匹配的数据")
        return

    # 2. 数据对齐检查
    total_count = len(drama_values)
    # 确保数据量是 gpu_nums 的整数倍，如果不是，截断末尾多余的
    if total_count % gpu_nums != 0:
        remainder = total_count % gpu_nums
        print(f"警告: 数据总数({total_count})不是 {gpu_nums} 的倍数，将丢弃最后 {remainder} 条数据。")
        drama_values = drama_values[:-remainder]
        
    data = []
    # 3. 按步长 gpu_nums 遍历数据
    # range(start, stop, step) -> 0, gpu_nums, 2*gpu_nums, ...
    for i in range(0, len(drama_values), gpu_nums):
        step_index = i // gpu_nums
        # 切片获取这一组的 gpu_nums 个数据
        group_values = drama_values[i : i + gpu_nums]
        
        # 计算平均值
        mean_val = sum(group_values) / gpu_nums
        if mean_val == 0:
            continue
        data.append({'step': len(data), 'mean': round(mean_val * 100, 1)})

    df = pd.DataFrame(data)
    
    # 4. 保存结果
    df.to_csv(output_path, index=False)
    print(f"处理完成 (gpu_nums={gpu_nums})，结果已保存至: {output_path}")
    print(df.head()) # 打印前几行预览

# =================配置区域=================
log_file = './log/eagle3.log'
csv_file = './csv/eagle3.csv'
gpu_nums = 2  # <--- 在这里修改 GPU 数量 (标量)
# =========================================

if __name__ == "__main__":
    process_log_file(log_file, csv_file, gpu_nums)