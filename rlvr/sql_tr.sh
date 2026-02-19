#!/bin/bash
MASTER_PORT=29501 \
NPROC_PER_NODE=2 \
swift rlhf \
    --rlhf_type grpo \
    --model ../../../models/Qwen3-4B-Instruct-2507/  \
    --external_plugins ./plugin.py \
    --reward_funcs json_precision \
    --use_vllm true \
    --train_type full \
    --vllm_mode server \
    --vllm_server_host 127.0.0.1 \
    --vllm_server_port 8083 \
    --torch_dtype bfloat16 \
    --dataset './Json-Precision' \
    --load_from_cache_file false \
    --max_length 2048 \
    --max_completion_length 1024 \
    --num_train_epochs 3 \
    --per_device_train_batch_size 8 \
    --per_device_eval_batch_size 8 \
    --learning_rate 5e-7 \
    --gradient_accumulation_steps 8 \
    --eval_steps 500 \
    --save_steps 100 \
    --save_total_limit 20 \
    --logging_steps 1 \
    --output_dir output/sql_gen \
    --warmup_ratio 0.01 \
    --dataloader_num_workers 4 \
    --num_generations 8 \
    --temperature 2.5 \
    --log_entropy true \
    --log_completions true \
    --beta 0.001 \
    --num_iterations 1 
