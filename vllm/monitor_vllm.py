import wandb
import time
import argparse
import numpy as np
from nvitop import Device

def parse_gpu_ids(gpu_str):
    """解析 '0,1,2' 格式的字符串为整数列表"""
    if not gpu_str:
        return []
    try:
        return [int(x) for x in gpu_str.split(',')]
    except ValueError:
        print(f"❌ 错误: GPU ID 格式不正确 ('{gpu_str}')。请使用逗号分隔，如 '0,1'")
        exit(1)

def main():
    # --- 1. 参数配置 ---
    parser = argparse.ArgumentParser(description="Monitor specific GPUs for vLLM via WandB")
    parser.add_argument("--project", type=str, default="vllm-inference-analysis", help="WandB 项目名称")
    parser.add_argument("--name", type=str, default='Qwen3-32B-RedHatAI_aider', help="WandB Run Name (可选)")
    parser.add_argument("--interval", type=float, default=0.5, help="采样间隔(秒)")
    parser.add_argument("--gpus", type=str, default='1,5', help="指定监控的GPU ID，用逗号分隔 (例如: '0,1' 或 '4,5,6,7')。默认监控所有可见GPU。")
    
    args = parser.parse_args()

    # --- 2. 确定要监控的设备 ---
    all_devices = Device.all()
    target_devices = []
    target_ids = []

    if args.gpus:
        # 用户指定了特定的 GPU
        requested_ids = parse_gpu_ids(args.gpus)
        # 验证 ID 是否存在
        max_id = len(all_devices) - 1
        for gid in requested_ids:
            if gid > max_id:
                print(f"❌ 错误: 找不到 GPU {gid}。当前机器只有 GPU 0-{max_id}。")
                exit(1)
            target_devices.append(Device(gid)) # 实例化特定 GPU
            target_ids.append(gid)
    else:
        # 默认监控所有
        target_devices = all_devices
        target_ids = [d.index for d in all_devices]

    # 生成一个用于 WandB 显示的组名，例如 "GPUs_0-1"
    ids_str = "-".join(map(str, target_ids))
    group_label = f"GPUs_{ids_str}"
    
    print(f"🔍 正在初始化监控...")
    print(f"🎯 目标设备 ID: {target_ids}")
    print(f"🏷️  WandB 指标前缀: '{group_label}/...'")

    # --- 3. 初始化 WandB ---
    # 如果没有提供 run name，自动加上 GPU 信息方便区分
    run_name = args.name if args.name else f"monitor_gpus_{ids_str}"
    
    wandb.init(project=args.project, name=run_name)
    
    print(f"🚀 开始监控! (Run: {run_name})")
    print("❌ 按 Ctrl+C 停止")

    try:
        while True:
            metrics = {}
            
            # 用于计算这组 GPU 平均值的临时列表
            group_sm_utils = []
            group_mem_bws = []
            
            # --- 4. 遍历指定设备采集数据 ---
            for device in target_devices:
                snapshot = device.as_snapshot()
                
                # 获取核心指标
                sm = snapshot.gpu_utilization
                mem_bw = snapshot.memory_utilization
                
                # 记录单卡数据 (方便 debug)
                # key 格式: "Detail/GPU_0_SM"
                metrics[f"Detail/GPU_{device.index}_SM"] = sm
                metrics[f"Detail/GPU_{device.index}_Mem_BW"] = mem_bw
                
                group_sm_utils.append(sm)
                group_mem_bws.append(mem_bw)

            # --- 5. 计算并记录平均值 (核心数据) ---
            # key 格式: "GPUs_0-1/Avg_SM_Utilization"
            # 这样画图时，你能清楚地知道这是哪几张卡的平均
            metrics[f"{group_label}/Avg_SM_Utilization"] = np.mean(group_sm_utils)
            metrics[f"{group_label}/Avg_Mem_Bandwidth"] = np.mean(group_mem_bws)
            
            # 发送数据
            wandb.log(metrics)
            
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n🛑 停止监控。")
        wandb.finish()

if __name__ == "__main__":
    main()