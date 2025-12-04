#!/bin/bash

# 设置环境变量
export PYTHONPATH=../../../:$PYTHONPATH
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export CUDA_VISIBLE_DEVICES=1
output_dir=v21_all_bge

# 运行训练命令
swift sft \
    --model ../../../../../models/Qwen3-Reranker-0.6B/ \
    --task_type generative_reranker \
    --loss_type generative_reranker \
    --train_type full \
    --dataset $output_dir/hisense-reranking \
    --eval_strategy steps \
    --eval_steps 50 \
    --num_train_epochs 600000 \
    --lr-scheduler-type cosine \
    --save_steps 50000 \
    --per_device_train_batch_size 4 \
    --per_device_eval_batch_size 4 \
    --gradient_accumulation_steps 1 \
    --dataset_num_proc 8 \
    --learning_rate 6e-6 \
    --label_names labels \
    --dataloader_drop_last true \
    --no_load_from_cache_file \
    --column '{"pos":"positive","neg":"negative"}' \
    --output_dir $output_dir
