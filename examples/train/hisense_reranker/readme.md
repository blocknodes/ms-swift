数据格式：
example_data.jsonl

将pos/neg中的item中的filename和content提取出来，组成dict的jq命令：
jq '.pos |= map( split("\n") | {filename: .[0], content: (.[1:] | join("\n"))} ) | .neg |= map( split("\n") | {filename: .[0], content: (.[1:] | join("\n"))} )' /data/db/data/ali_new.jsonl



将filenam w/o concat

jq -c '
.pos |= map(
  .,
  {content: "\(.filename)\n\(.content)", filename: .filename}
) |
.neg |= map(
  .,
  {content: "\(.filename)\n\(.content)", filename: .filename}
)
' example.jsonl>example.jsonl.filename

打分用于self-distillation
python add_pos_neg_score_with_qwen_reranker.py --input example_data.jsonl.filename --output example_data.jsonl.filename.score

example_data.jsonl.filename.score可直接用于训练，配合soft_label_exp branch

示例：

python json_handler/json_process.py  --input  bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3 --output bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase --processor json_handler/filename_badcase.py:example_processor --debug
python json_handler/json_process.py  --input   bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase  --output bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train  --processor json_handler/faq_train.py:example_processor --debug
python json_handler/json_process.py  --input   bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase  --output bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train  --processor json_handler/prefix_suffix_train.py:example_processor --debug
python json_handler/json_process.py  --input    bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train --output processed_data/ge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train.swift   --processor json_handler/fit_swift.py:example_processor --debug
python json_handler/json_process.py  --input   processed_data/ge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train.swift --output processed_data/ge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train.swift.score   --processor json_handler/score.py:example_processor --debug
python json_handler/json_process.py  --input   processed_data/ge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train.swift --output processed_data/ge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train.swift.score   --processor json_handler/score.py:example_processor --debug
python json_handler/json_process.py  --input  bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3 --output bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase --processor json_handler/filename_badcase.py:example_processor
python json_handler/json_process.py  --input   bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase  --output bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train  --processor json_handler/prefix_suffix_train.py:example_processor
python json_handler/json_process.py  --input    bge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train --output processed_data/ge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train.swift   --processor json_handler/fit_swift.py:example_processor --debug
python json_handler/json_process.py  --input   processed_data/ge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train.swift --output processed_data/ge_m3_emb_0721_5_5_val2.jsonl.benchmark.score.llmjudge.hit1hit3.filnamebadcase.train.swift.score   --processor json_handler/score.py:example_processor --debug