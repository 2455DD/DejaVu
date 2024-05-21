#!/bin/bash
#SBATCH --job-name=opt
#
#SBATCH --partition=sphinx
#SBATCH --gres=gpu:1
#SBATCH --time=3:59:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=8G
#SBATCH --output=/afs/cs.stanford.edu/u/biyuan/exe_log/opt_%j.log
port=$1

source activate base                          # Activate my conda python environment
cd /sailhome/biyuan/GPT-home-private     # Change directory

nvidia-smi

ls -l /sys/class/net/
netif=`echo "import os; print(sorted([x for x in os.listdir('/sys/class/net/') if x.startswith('en')])[0])" | python`
echo setting network interface to $netif
export NCCL_SOCKET_IFNAME=$netif
export GLOO_SOCKET_IFNAME=$netif
export NCCL_DEBUG=INFO
export NCCL_IB_DISABLE=1
export NCCL_P2P_DISABLE=1

world_size=8
machine_size=8
n_gpu_per_machine=$((world_size/machine_size))
infer_data={{infer_data}}

i=0
while :
do
  if [ "$i" -ge "$n_gpu_per_machine" ]; then
      break
  fi
  
  DIST_CONF="--pp-mode pipe_sync_sample_mask_token_pipe --pipeline-group-size $world_size --cuda-id $i"
  MODEL_CONF="--model-type opt --model-name /sailhome/biyuan/fm/models/opt-175b-new --num-iters 9999999999999"
  INFERENCE_CONF="--fp16  --budget 20400 --batch-size 24 --input-seq-length 512 --generate-seq-length 32 --micro-batch-size 1 --num-layers 12 --max-layers 96 --infer-data $infer_data"
  COOR_CONF="--coordinator-server-ip 10.79.12.70  --unique-port $port"

  python -u dist_inference_runner_w_slurm_coordinator.py $DIST_CONF $MODEL_CONF $INFERENCE_CONF $COOR_CONF &

  ((port++))
  ((i++))

done

wait
