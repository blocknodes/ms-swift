#!/bin/bash

# 设置训练所需的环境变量和参数
export nproc_per_node=2
export PYTHONPATH=../../../:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0,1
export NPROC_PER_NODE=$nproc_per_node
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# 运行训练命令
swift sft \
    --model /data/db/models/Qwen3-Reranker-0.6B/ \
    --task_type generative_reranker \
    --loss_type generative_reranker \
    --train_type full \
    --dataset /data/db/data/hisense-reranking \
    --split_dataset_ratio 0.1 \
    --eval_strategy steps \
    --eval_steps 10 \
    --num_train_epochs 100 \
    --save_steps 50 \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --gradient_accumulation_steps $((8 / nproc_per_node)) \
    --dataset_num_proc 8 \
    --learning_rate 6e-6 \
    --label_names labels \
    --dataloader_drop_last true \
    --no_load_from_cache_file \
    --column '{"pos":"positive","neg":"negative"}' \
    --gradient_checkpointing_kwargs '{"use_reentrant": false}' \
    --output_dir badcase
    
    #--val_dataset  /data/db/data/hisense-reranking \
