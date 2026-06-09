import os
import shutil

def delete_folders_starting_with(target_path, prefix):
    # 检查路径是否存在
    if not os.path.exists(target_path):
        print(f"路径不存在: {target_path}")
        return

    # 遍历目标文件夹下的所有内容
    for item in os.listdir(target_path):
        full_path = os.path.join(target_path, item)
        
        # 判断条件：1. 是文件夹 2. 以指定前缀开头
        if os.path.isdir(full_path) and item.startswith(prefix):
            try:
                print(f"正在删除: {full_path}")
                shutil.rmtree(full_path) # 等同于 rm -rf
            except Exception as e:
                print(f"删除失败 {full_path}: {e}")

if __name__ == "__main__":
    # --- 配置区域 ---
    target_directory = "tmp.benchmarks/" # 修改你的路径
    target_prefix = "2025"
    # ----------------
    
    # 二次确认，防止误操作
    confirm = input(f"警告：这将永久删除 {target_directory} 下所有以 '{target_prefix}' 开头的文件夹。\n确认请输入 'yes': ")
    
    if confirm.lower() == 'yes':
        delete_folders_starting_with(target_directory, target_prefix)
        print("完成。")
    else:
        print("操作已取消。")