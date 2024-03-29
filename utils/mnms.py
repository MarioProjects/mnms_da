from models import model_selector
from utils.dataload import save_nii
from utils.datasets import dataset_selector
from models.gan import define_Gen
from utils.data_augmentation import data_augmentation_selector
import torch
import os

from utils.general import binarize_volume_prediction, plot_save_pred_volume


def test_prediction(args, model=None, generator=None):

    os.makedirs(os.path.join(args.output_dir, "test_predictions"), exist_ok=True)
    if hasattr(args, 'generated_overlays') and args.generated_overlays > 0:
        os.makedirs(os.path.join(args.output_dir, "overlays", "test_evaluation"), exist_ok=True)

    _, _, val_aug = data_augmentation_selector(
        args.data_augmentation, args.img_size, args.crop_size, args.mask_reshape_method
    )
    test_loader = dataset_selector(_, _, val_aug, args, is_test=True)

    if model is None:
        print("\n[WARNING] Test evaluation using a Random Model!\n")
        model = model_selector(
            args.problem_type, args.model_name, test_loader.dataset.num_classes, from_swa=args.swa_checkpoint,
            in_channels=3 if args.add_depth else 1, devices=args.gpu, checkpoint=args.model_checkpoint
        )

    if generator is None:
        if args.gen_checkpoint != "":
            print("Using Generator!")
            generator = define_Gen(
                input_nc=3 if args.add_depth else 1, output_nc=3 if args.add_depth else 1, ngf=args.ngf,
                netG=args.gen_net, norm=args.norm_layer, use_dropout=not args.no_dropout, gpu_ids=args.gpu,
                checkpoint=args.gen_checkpoint
            )

    model.eval()
    with torch.no_grad():
        for (ed_volume, es_volume, img_affine, img_header, img_shape, img_id, original_ed, original_es) in test_loader:

            ed_volume = ed_volume.type(torch.float).cuda()
            es_volume = es_volume.type(torch.float).cuda()

            if generator is not None:
                ed_volume = generator(ed_volume)
                es_volume = generator(es_volume)

            prob_pred_ed = model(ed_volume)
            prob_pred_es = model(es_volume)

            pred_ed = binarize_volume_prediction(prob_pred_ed, img_shape, "padd")  # [slices, height, width]
            pred_es = binarize_volume_prediction(prob_pred_es, img_shape, "padd")  # [slices, height, width]

            pred_ed = pred_ed.transpose(1, 2, 0)  # [height, width, slices]
            pred_es = pred_es.transpose(1, 2, 0)  # [height, width, slices]

            save_nii(
                os.path.join(args.output_dir, "test_predictions", "{}_sa_ED.nii.gz".format(img_id)),
                pred_ed, img_affine, img_header
            )

            save_nii(
                os.path.join(args.output_dir, "test_predictions", "{}_sa_ES.nii.gz".format(img_id)),
                pred_es, img_affine, img_header
            )

            if hasattr(args, 'generated_overlays') and args.generated_overlays > 0:
                plot_save_pred_volume(
                    original_ed, pred_ed, os.path.join(args.output_dir, "overlays", "test_evaluation"),
                    "{}_ed".format(img_id)
                )
                plot_save_pred_volume(
                    original_ed, pred_ed, os.path.join(args.output_dir, "overlays", "test_evaluation"),
                    "{}_es".format(img_id)
                )
                args.generated_overlays -= 1