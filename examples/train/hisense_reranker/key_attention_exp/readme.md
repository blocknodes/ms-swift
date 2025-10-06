```
python json_handler/json_process.py --processor key_attention_exp/faq_train.py:example_processor --input key_attention_exp/knowlege_human_label.jsonl --output key_attention_exp/knowlege_human_label.jsonl.split_sets
python key_attention_exp/reduce_generate_train.py key_attention_exp/knowlege_human_label.jsonl.split_sets    key_attention_exp/knowlege_human_label.jsonl.split_sets.4groups
python json_handler/json_process.py --processor key_attention_exp/4group2train.py:example_processor --input key_attention_exp/knowlege_human_label.jsonl.split_sets.4groups --output key_attention_exp/knowlege_human_label.jsonl.split_sets.4groups.posneg
python json_handler/json_process.py --processor json_handler/score.py:example_processor --input key_attention_exp/knowlege_human_label.jsonl.split_sets.4groups.posneg --output key_attention_exp/knowlege_human_label.jsonl.split_sets.4groups.posneg.score
python json_handler/json_process.py --processor json_handler/fit_swift.py:example_processor --input key_attention_exp/knowlege_human_label.jsonl.split_sets.4groups.posneg.score --output key_attention_exp/knowlege_human_label.jsonl.split_sets.4groups.posneg.score.swift
cp key_attention_exp/knowlege_human_label.jsonl.split_sets.4groups.posneg.score.swift v8_without_reranker_and_content/hisense-reranking/train/
```

实验结果：
```
python json_handler/json_process.py --processor json_handler/score.py:example_processor --input processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model --output processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_bge
python json_handler/json_process.py --processor json_handler/eval.py:example_processor --input processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_bge  --output processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_bge.hit
python json_handler_reduce/reduce_hit1hit3.py  processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_bge.hit
python json_handler/json_process.py --processor json_handler/score.py:example_processor --input processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model --output processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_qwen
python json_handler/json_process.py --processor key_attention_exp/score_key.py:example_processor --input  processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_qwen --output processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_qwen_model
python json_handler/json_process.py --processor json_handler/eval.py:example_processor --input processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_qwen_model  --output processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_qwen_model.hit
python json_handler_reduce/reduce_hit1hit3.py processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_qwen_model.hit
python json_handler/json_process.py --processor json_handler/eval.py:example_processor --input processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_qwen  --output processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_qwen.hit
python json_handler_reduce/reduce_hit1hit3.py processed_data/bge_m3_emb_0721_5_5_val2.jsonl.filename.has_model.score_qwen.hit
```

原始qwen：
hit1:0.2643312101910828, hit3:0.6464968152866242
qwen+model：
hit1:0.4840764331210191, hit3:0.8789808917197452
bert-0822:
hit1:0.46178343949044587, hit3:0.7929936305732485


精确匹配模型：
python serve_qw_reranker.py /juice/workspace/ms-swift/examples/train/hisense_reranker/v9_random_string_test/v3-20251006-112820/checkpoint-300/