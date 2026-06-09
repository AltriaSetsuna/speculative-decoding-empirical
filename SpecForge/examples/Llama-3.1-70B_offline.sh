SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$(dirname $SCRIPT_DIR)
NUM_GPUS=4
TP_SIZE=4
BUILD_DATASET_NUM_PROC=32



# # generate hidden states
# CUDA_VISIBLE_DEVICES=1,3,4,5 \
# torchrun \
#     --standalone \
#     --nproc_per_node $NUM_GPUS \
#     scripts/prepare_hidden_states.py \
#     --target-model-path meta-llama/Llama-3.1-70B-Instruct \
#     --enable-aux-hidden-states \
#     --data-path $ROOT_DIR/cache/dataset/Llama-3.1-70B-Instruct/ST.jsonl \
#     --output-path $ROOT_DIR/cache/hidden_states/ST_train_Llama-3.1-70B-Instruct \
#     --chat-template llama3 \
#     --build-dataset-num-proc $BUILD_DATASET_NUM_PROC \
#     --max-length 15000 \
#     --tp-size $TP_SIZE \
#     --batch-size 4 




# train eagle3 offline
NUM_GPUS=4
TP_SIZE=1
CUDA_VISIBLE_DEVICES=1,3,4,5 \
torchrun \
    --standalone \
    --nproc_per_node $NUM_GPUS \
    $ROOT_DIR/scripts/train_eagle3.py \
    --target-model-path meta-llama/Llama-3.1-70B-Instruct \
    --draft-model-config $ROOT_DIR/configs/llama3-70B-ealge3.json \
    --train-data-path $ROOT_DIR/cache/dataset/Llama-3.1-70B-Instruct/ST.jsonl \
    --train-hidden-states-path $ROOT_DIR/cache/hidden_states/ST_train_Llama-3.1-70B-Instruct \
    --build-dataset-num-proc $BUILD_DATASET_NUM_PROC \
    --output-dir $ROOT_DIR/outputs/Llama-3.1-70B-eagle3-ST-offline_7 \
    --num-epochs 1 \
    --batch-size 1 \
    --tp-size 1 \
    --target-model-backend sglang \
    --learning-rate 5e-6 \
    --max-length 15000 \
    --chat-template llama3 \
    --cache-dir $ROOT_DIR/cache \
    --resume \
