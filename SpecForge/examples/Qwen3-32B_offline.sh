SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$(dirname $SCRIPT_DIR)

echo $SCRIPT_DIR
echo $ROOT_DIR
NUM_GPUS=6
TP_SIZE=2
BUILD_DATASET_NUM_PROC=32



# # generate hidden states
# CUDA_VISIBLE_DEVICES=0,1,2,3,4,5 \
# torchrun \
#     --standalone \
#     --nproc_per_node $NUM_GPUS \
#     scripts/prepare_hidden_states.py \
#     --target-model-path Qwen/Qwen3-32B \
#     --enable-aux-hidden-states \
#     --data-path $ROOT_DIR/cache/dataset/Qwen3-32B/ST.jsonl \
#     --output-path $ROOT_DIR/cache/hidden_states/ST_train_Qwen3-32B \
#     --chat-template qwen \
#     --build-dataset-num-proc $BUILD_DATASET_NUM_PROC \
#     --max-length 15000 \
#     --tp-size $TP_SIZE \
#     --batch-size 4 
d


export HF_HUB_OFFLINE=1
# train eagle3 offline
NUM_GPUS=2
TP_SIZE=1
CUDA_VISIBLE_DEVICES=4,5 \
torchrun \
    --standalone \
    --nproc_per_node $NUM_GPUS \
    $ROOT_DIR/scripts/train_eagle3.py \
    --target-model-path Qwen/Qwen3-32B \
    --draft-model-config $ROOT_DIR/configs/qwen3-32b-eagle3.json \
    --train-data-path $ROOT_DIR/cache/dataset/Qwen3-32B/ST.jsonl \
    --train-hidden-states-path $ROOT_DIR/cache/hidden_states/ST_train_Qwen3-32B \
    --build-dataset-num-proc $BUILD_DATASET_NUM_PROC \
    --output-dir $ROOT_DIR/outputs/Qwen3-32B-offline \
    --num-epochs 2 \
    --batch-size 1 \
    --tp-size 1 \
    --target-model-backend sglang \
    --learning-rate 5e-6 \
    --max-length 15000 \
    --chat-template qwen \
    --cache-dir $ROOT_DIR/cache \
