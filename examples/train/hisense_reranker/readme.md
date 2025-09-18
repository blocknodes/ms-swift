数据格式：
example_data.jsonl

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
' example_data.jsonl >example_data.jsonl.filename

打分用于self-distillation
python add_pos_neg_score_with_qwen_reranker.py --input example_data.jsonl.filename --output example_data.jsonl.filename.score

example_data.jsonl.filename.score可直接用于训练，配合soft_label_exp branch