#!/bin/bash

# 设置环境变量
export PYTHONPATH=../../../:$PYTHONPATH
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
#export CUDA_VISIBLE_DEVICES=1
output_dir=v3filename_pos_neg

# 运行训练命令
/usr/bin/python -m torch.distributed.run --nproc_per_node 1 \
    /juice/prd_ai_center/train_project/dingbo4/workspace/ms-swift/swift/cli/sft.py \
    --model ../../../../../models/Qwen3-Reranker-0.6B/ \
    --task_type generative_reranker \
    --loss_type generative_reranker \
    --train_type full \
    --dataset $output_dir/hisense-reranking \
    --split_dataset_ratio 0.05 \
    --eval_strategy steps \
    --eval_steps 50 \
    --num_train_epochs 20 \
    --lr-scheduler-type constant \
    --save_steps 50 \
    --per_device_train_batch_size 8 \
    --per_device_eval_batch_size 8 \
    --gradient_accumulation_steps 1 \
    --dataset_num_proc 8 \
    --learning_rate 6e-6 \
    --label_names labels \
    --dataloader_drop_last true \
    --no_load_from_cache_file \
    --column '{"pos":"positive","neg":"negative"}' \
    --output_dir $output_dir
