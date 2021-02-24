#!/usr/bin/env python
# coding: utf-8

# ---- My utils ----
from models import model_selector
from utils.arguments import *
from utils.data_augmentation import data_augmentation_selector
from utils.datasets import dataset_selector, coral_dataset_selector
from utils.logging import log_epoch, build_header
from utils.neural import *

set_seed(args.seed)

if args.coral and args.coral_vendors is None:
    assert False, "When coral selected specify which vendors use with '--coral_vendors'"

train_aug, train_aug_img, val_aug = data_augmentation_selector(
    args.data_augmentation, args.img_size, args.crop_size, args.mask_reshape_method
)
train_loader, val_loader, num_classes, class_to_cat, include_background = dataset_selector(train_aug, train_aug_img, val_aug, args)
train_coral_loader = coral_dataset_selector(train_aug, train_aug_img, "Training", args) if args.coral else None
val_coral_loader = coral_dataset_selector(val_aug, [], "Validation", args) if args.coral else None
print(f"Number of classes: {num_classes}")

model = model_selector(
    args.problem_type, args.model_name, num_classes,
    in_channels=3 if args.add_depth else 1, devices=args.gpu, checkpoint=args.model_checkpoint
)
swa_model = None

criterion, weights_criterion, multiclass_criterion = get_criterion(args.criterion, args.weights_criterion)
optimizer = get_optimizer(args.optimizer, model, lr=args.learning_rate)

scheduler = get_scheduler(
    args.scheduler, optimizer, epochs=args.epochs,
    min_lr=args.min_lr, max_lr=args.max_lr, scheduler_steps=args.scheduler_steps
)

swa_scheduler = get_scheduler("swa", optimizer, max_lr=args.swa_lr) if args.swa_start != -1 else None

train_metrics = MetricsAccumulator(
    args.problem_type, args.metrics, num_classes, average="mean",
    include_background=include_background, mask_reshape_method=args.mask_reshape_method
)
val_metrics = MetricsAccumulator(
    args.problem_type, args.metrics, num_classes, average="mean",
    include_background=include_background, mask_reshape_method=args.mask_reshape_method
)

full_criterion = [args.criterion]
full_criterion += ["coral"] if args.coral else ""

header, defrosted = build_header(class_to_cat, full_criterion, args.metrics, display=True), False
for current_epoch in range(args.epochs):

    defrosted = check_defrost(model, defrosted, current_epoch, args.defrost_epoch)

    train_metrics = train_step(
        train_loader, model, criterion, weights_criterion, multiclass_criterion, optimizer, train_metrics,
        args.coral, train_coral_loader, args.coral_weight, args.vol_task_weight, num_classes
    )

    val_metrics = val_step(
        val_loader, model, val_metrics, criterion, weights_criterion, multiclass_criterion, num_classes,
        generated_overlays=args.generated_overlays, overlays_path=f"{args.output_dir}/overlays/epoch_{current_epoch}"
    )

    # ToDo
    if args.coral: val_metrics.add_losses("Coral_loss", 0.0000)

    current_lr = get_current_lr(optimizer)
    log_epoch((current_epoch + 1), current_lr, train_metrics, val_metrics, header)

    val_metrics.save_progress(args.output_dir, identifier="validation_metrics")
    train_metrics.save_progress(args.output_dir, identifier="train_metrics")

    if args.swa_start != -1 and (current_epoch + 1) >= args.swa_start:
        if not swa_model:
            print("\n------------------------------- START SWA -------------------------------\n")
            swa_model = torch.optim.swa_utils.AveragedModel(model)
        else:
            swa_model.update_parameters(model)
            swa_scheduler.step()
    else:
        # Only save checkpoints when not applying SWA -> only want save last model using SWA
        create_checkpoint(val_metrics, model, args.model_name, args.output_dir)
        scheduler_step(optimizer, scheduler, val_metrics, args)

print("\nBest Validation Results:")
val_metrics.report_best()

finish_swa(
    swa_model, train_loader, val_loader, criterion, weights_criterion, multiclass_criterion,
    num_classes, include_background, args
)
