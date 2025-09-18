#!/bin/bash

# 设置环境变量
export PYTHONPATH=../../../:$PYTHONPATH
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export CUDA_VISIBLE_DEVICES=1

# 运行训练命令
swift sft \
    --model /data/db/models/Qwen3-Reranker-0.6B/ \
    --task_type generative_reranker \
    --loss_type generative_reranker \
    --train_type full \
    --dataset /data/db/data/hisense-reranking \
    --val_dataset /data/db/data/hisense-reranking \
    --eval_strategy steps \
    --eval_steps 5 \
    --num_train_epochs 2 \
    --save_steps 10 \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 4 \
    --gradient_accumulation_steps 8 \
    --dataset_num_proc 8 \
    --learning_rate 6e-6 \
    --label_names labels \
    --dataloader_drop_last true \
    --no_load_from_cache_file \
    --column '{"pos":"positive","neg":"negative"}' \
    --output_dir output
