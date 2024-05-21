file=../lm-eval-harness-adapter/wsc.jsonl
output_file=../lm-eval-harness-adapter/output_wsc.jsonl


echo "start running ${file}"
export SPRARSE_PATH=$PATH_TO_SPARSITY_PREDICTOR
export LAYER=86
export TOPK=5000
export ATTN_TOPK_1=24
export ATTN_TOPK_2=48
export SPARSE_ATT=1

LAYER=86
TOPK=5000
ATTN_TOPK_1=24
ATTN_TOPK_2=48

ARGS="--model-name /content/checkpoint/opt-175b-new \
--model-type opt-ml-att-sparse \
--seed 42 \
--fp16 \
--num-layers 12 \
--max-layers 96 \
--budget 22800 \
--num-iters 1000000 \
--dist-url tcp://127.0.0.1:9031 \
--token-micro-batch-size 1 \
--world-size 8 --pipeline-group-size 8 --data-group-size 1 \
--pp-mode pipe_sync_sample_mask_token_pipe \
--infer-data ${file} \
--output-path ${output_file}"

(trap 'kill 0' SIGINT; \
python dist_inference_runner.py $(echo ${ARGS}) --cuda-id 0 --rank 0 \
    &
python dist_inference_runner.py $(echo ${ARGS}) --cuda-id 1 --rank 1 \
    &
python dist_inference_runner.py $(echo ${ARGS}) --cuda-id 2 --rank 2 \
    &
python dist_inference_runner.py $(echo ${ARGS}) --cuda-id 3 --rank 3 \
    &
python dist_inference_runner.py $(echo ${ARGS}) --cuda-id 4 --rank 4 \
    &
python dist_inference_runner.py $(echo ${ARGS}) --cuda-id 5 --rank 5 \
    &
python dist_inference_runner.py $(echo ${ARGS}) --cuda-id 6 --rank 6 \
    &
python dist_inference_runner.py $(echo ${ARGS}) --cuda-id 7 --rank 7 \
    & \
wait)