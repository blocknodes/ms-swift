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