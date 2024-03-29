#!/bin/bash

# Check if MMs data is available, if not download
if [ ! -d "data/MMs" ]
then
    echo "MMs data not found at 'data' directory. Downloading..."
    wget -nv --load-cookies /tmp/cookies.txt \
      "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt \
      --keep-session-cookies --no-check-certificate \
      'https://docs.google.com/uc?export=download&id=1g8vqf47A2KKnng1SIj5uxRaPsmrwqtki' \
      -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1g8vqf47A2KKnng1SIj5uxRaPsmrwqtki" \
      -O MMs_Oficial.tar.gz && rm -rf /tmp/cookies.txt
    mkdir -p data
    tar -zxf MMs_Oficial.tar.gz  -C data/
    rm MMs_Oficial.tar.gz
    echo "Done!"
else
  echo "MMs data found at 'data' directory!"
fi

# Only download the data argument ./tests/segmentation/mms2d.sh only_data
if [[ $1 == "only_data" ]]
then
  exit
fi

gpu="0,1"
dataset="mms2d"
problem_type="segmentation"

# Available models:
#   -> resnet34_unet_scratch - resnet18_unet_scratch
#   -> small_segmentation_unet - small_segmentation_small_unet
#      small_segmentation_extrasmall_unet - small_segmentation_nano_unet
#   -> resnet18_pspnet_unet - resnet34_pspnet_unet
model="resnet18_unet_scratch"

img_size=224
crop_size=224
batch_size=32

epochs=200
swa_start=130
defrost_epoch=-1

# Available schedulers:
# constant - steps - plateau - one_cycle_lr (max_lr) - cyclic (min_lr, max_lr, scheduler_steps)
scheduler="steps"
lr=0.001
swa_lr=0.00256
# Available optimizers:
# adam - sgd - over9000
optimizer="adam"

# Available data augmentation policies:
# "none" - "random_crops" - "rotations" - "vflips" - "hflips" - "elastic_transform" - "grid_distortion" - "shift"
# "scale" - "optical_distortion" - "coarse_dropout" or "cutout" - "downscale"
data_augmentation="mms2d"

normalization="standardize"  # reescale - standardize
mask_reshape_method="padd"  # padd - resize

generated_overlays=32

# Available criterions:
# bce - bce_dice - bce_dice_ac - bce_dice_border - bce_dice_border_ce
#criterion="bce_dice_border_ce"
#weights_criterion="0.5,0.2,0.2,0.2,0.5"
criterion="bce_dice"
weights_criterion="0.4, 0.5, 0.1"

output_dir="results/$dataset/$model/$optimizer/${scheduler}_lr${lr}/${criterion}_weights${weights_criterion}"
output_dir="$output_dir/normalization_${normalization}/da${data_augmentation}"

model_checkpoint="checkpoints/model_resnet18_unet_scratch_best_iou.pt"

python3 -u predict.py --gpu $gpu --dataset $dataset --model_name $model --img_size $img_size --crop_size $crop_size \
--batch_size $batch_size --normalization $normalization --output_dir "$output_dir" \
--problem_type $problem_type --mask_reshape_method $mask_reshape_method --metrics iou dice \
--generated_overlays $generated_overlays --add_depth --model_checkpoint "$model_checkpoint" --notify
#--swa_checkpoint

python3 -u tools/metrics_mnms.py --GT_IMG "data/MMs/Testing" --PRED_IMG "$output_dir/test_predictions"
