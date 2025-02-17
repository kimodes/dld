import numpy as np
import argparse
import torch
import os
from tqdm import tqdm
import scipy.io
from scipy import interpolate

from dataset import BrainDataset, FACE_OBJECT, MALE_FEMALE, ARTIFICIAL_NATURAL, CLASSIFY_ALL
from dataset import DATA_TYPE_TRAIN, DATA_TYPE_VALIDATION, DATA_TYPE_TEST
from model import get_eeg_model
from options import get_grad_cam_args
from utils import get_device, fix_state_dict, save_result, get_test_subject_ids
from utils import sigmoid
from guided_bp import GuidedBackprop
from model_stnn import calc_required_level


DEBUGGING = False

def calc_all_active_positions(level_size, kernel_size):
    all_positions = []
    handover_hop_size = 0
    for level in range(level_size-1, -1, -1):
        dilation_size = 2 ** level

        reverse_positions = [0]
        hop_size = (kernel_size-1) * 2 + handover_hop_size
        for i in range(hop_size):
            reverse_position = dilation_size * (i+1)
            reverse_positions.append(reverse_position)

        handover_hop_size = hop_size * 2
        positions = []
        for reverse_position in reverse_positions:
            position = 250 - 1 - reverse_position
            if position >= 0:
                positions.append(position)

        positions.reverse()
        all_positions.append(positions)

    all_positions.reverse()    
    return all_positions

def calc_effective_size(kernel_size, level):
    effective_size = 0
    for i in range(level):
        dilation_size = 2 ** i
        effective_size += (dilation_size * 2)
    return effective_size

def calc_interpolate_base_positions(kernel_size, level, active_positions):
    """
    Level must be specified to a value starting from 0
    (If kernel_size=2; 0~6)
    """
    dilation_size = 2 ** level
    effective_size = calc_effective_size(kernel_size, level)
    
    half_effective_size = effective_size//2
    interpolate_base_positions = \
        [active_position - half_effective_size for active_position in active_positions]
    # This value can be negative because it is just for the key point of the interpolation source
    return interpolate_base_positions

def interpolate_values(values, kernel_size, level, active_positions):
    if len(values) == 250:
        return values
    
    x_base = calc_interpolate_base_positions(kernel_size, level, active_positions)
    
    values = list(values)
    assert type(values) == list
    assert type(x_base) == list
    
    # When inserting 0 in frame 0 and frame 249
    if x_base[0] > 0:
        x_base = [0] + x_base
        values = [0] + values
    if x_base[-1] < 249:
        x_base = x_base + [249]
        values = values + [0]
    
    # When inserting values of first frame in frame 0 and that of last frame in frame 249
    """
    if x_base[0] > 0:
        x_base = [0] + x_base
        values = [values[0]] + values
    if x_base[-1] < 249:
        x_base = x_base + [249]
        values = values + [values[-1]]
    """
    
    x = np.arange(250)
    interp = interpolate.PchipInterpolator(x_base, values)
    y = interp(x)
    return y


def get_eeg_grad_cam(model, data, label, kernel_size, level_size):
    model.eval()
    model.zero_grad()
    
    out = model.forward_grad_cam(data)
    out = torch.sum(out)
    
    logit = out.cpu().detach().numpy()
    predicted_prob = sigmoid(logit)

    if logit > 0:
        predicted_label = 1
    else:
        predicted_label = 0
        
    if label == 0:
        out = -out
        
    out.backward()
    
    raw_grads     = model.get_cam_gradients() # [(1, 63, 250), ... x7]
    raw_features  = model.get_cam_features()  # [(1, 63, 250), ... x7]
    
    # Remove batch size 1. To np.ndarray
    raw_grads    = [raw_grad[0].cpu().numpy()             for raw_grad    in raw_grads]
    raw_features = [raw_feature[0].cpu().detach().numpy() for raw_feature in raw_features]

    model.clear_grad_cam()
    
    raw_grads    = np.array(raw_grads)
    raw_features = np.array(raw_features)
    # (7, 63, 250)
    
    all_active_positions = calc_all_active_positions(level_size, kernel_size)
    
    all_flat_active_grads    = []
    all_flat_active_features = []

    all_grad_cam_nopool_interpolated = []
    all_grad_cam_org_interpolated    = []
    
    for i,active_positions in enumerate(all_active_positions):
        active_grads    = raw_grads[i][:,active_positions]
        active_features = raw_features[i][:,active_positions]
        # e.g., (63, 250), (63, 3)...

        # gradientのglobal pooling
        active_grads_pool = np.mean(active_grads, axis=1).reshape(63,1)
        # (63, 1)

        # Compute Grad-CAM (grad x feature)
        # Sum up along channel and apply ReLU
        # (without global pooling)
        grad_cam_nopool = np.maximum(
            np.sum(active_features * active_grads,      axis=0), 0)
        # (with global pooling)
        grad_cam_org    = np.maximum(
            np.sum(active_features * active_grads_pool, axis=0), 0)

        # Expand to 250 frames
        grad_cam_nopool_interpolated = interpolate_values(
            grad_cam_nopool, kernel_size, i, active_positions)
        grad_cam_org_interpolated    = interpolate_values(
            grad_cam_org,    kernel_size, i, active_positions)

        all_grad_cam_nopool_interpolated.append(grad_cam_nopool_interpolated)
        all_grad_cam_org_interpolated.append(grad_cam_org_interpolated)
        
        all_flat_active_grads.append(active_grads.ravel())
        # Make the followings into 1-dimentional Flat: e.g., (63, 250), (63, 3)...
        # (To avoid errors when converting to ndarray at saving)
        all_flat_active_features.append(active_features.ravel())
        
    return raw_grads, raw_features, \
        np.array(all_grad_cam_nopool_interpolated), \
        np.array(all_grad_cam_org_interpolated), \
        all_flat_active_grads, all_flat_active_features, \
    

def get_eeg_cam(model, dataset, device, index, kernel_size, level_size):
    sample = dataset[index]
    
    s_data_e = sample['eeg_data'] # (5, 63, 250)
    s_label  = sample['label'] # (1,)
    label = int(s_label[0])
    
    # Add the dimension of the batch to the top of the data
    b_data_e = np.expand_dims(s_data_e, axis=0)
    
    # Convert to tensor
    b_data_e = torch.Tensor(b_data_e)

    # Transfer to the device
    b_data_e = b_data_e.to(device)
    
    gbp = GuidedBackprop(model)
    
    guided_bp0, predicted_prob0 = gbp.generate_gradients(b_data_e, 0, device)
    # (63, 250)
    if predicted_prob0 > 0.5:
        predicted_label = 1
    else:
        predicted_label = 0

    guided_bp1, predicted_prob1 = gbp.generate_gradients(b_data_e, 1, device)
    # (63, 250)

    # Free the memory of GuidedBP
    gbp.clear()
    
    # Compute Grad-CAM
    out0 = get_eeg_grad_cam(model, b_data_e, 0, kernel_size, level_size)
    raw_grads0, \
        raw_features0, \
        grad_cam_nopool0, \
        grad_cam_org0, \
        flat_active_grads0, \
        flat_active_features0 \
        = out0
    # (7, 63, 250),
    # (7, 63, 250),
    # (7, 63, 250),
    # (7, 63, 250),
    # [(63, 250), ..., (63, 3)],
    # [(63, 250), ..., (63, 3)]
    
    out1 = get_eeg_grad_cam(model, b_data_e, 1, kernel_size, level_size)
    raw_grads1, \
        raw_features1, \
        grad_cam_nopool1, \
        grad_cam_org1, \
        flat_active_grads1, \
        flat_active_features1 \
        = out1    

    return guided_bp0, guided_bp1, \
        raw_grads0, raw_grads1, \
        raw_features0, \
        grad_cam_nopool0, grad_cam_nopool1, \
        grad_cam_org0, grad_cam_org1, \
        flat_active_grads0, flat_active_grads1, \
        flat_active_features0, \
        label, predicted_label, predicted_prob0


def process_grad_cam_eeg_sub(args,
                             classify_type,
                             fold,
                             output_dir):
    
    if args.test:
        data_type = DATA_TYPE_TEST
    else:
        data_type = DATA_TYPE_VALIDATION

    test_subject_ids = get_test_subject_ids(args.test_subjects)

    dataset = BrainDataset(data_type=data_type,
                           classify_type=classify_type,
                           data_seed=args.data_seed,
                           use_fmri=False,
                           use_eeg=True,
                           data_dir=args.data_dir,
                           eeg_normalize_type=args.eeg_normalize_type,
                           eeg_frame_type=args.eeg_frame_type,
                           average_trial_size=args.average_trial_size,
                           average_repeat_size=args.average_repeat_size,
                           fold=fold,
                           test_subjects=test_subject_ids,
                           subjects_per_fold=args.subjects_per_fold,
                           debug=args.debug)

    device, use_cuda = get_device(args.gpu)
    
    model_path = "{}/model_ct{}_{}.pt".format(args.save_dir, classify_type, fold)
    state = torch.load(model_path, map_location=device)
    state = fix_state_dict(state)

    level_size = args.level_size

    if level_size < 0:
        level_size = calc_required_level(args.kernel_size)
    
    model = get_eeg_model(args.model_type, False, args.kernel_size, level_size, args.level_hidden_size,
                          args.residual, device)
    model.load_state_dict(state)
    
    data_size = len(dataset)

    # Since "cam_feature" and "active_cam_feature" are the same for both labe=0 and 1, save only one of them each
    guided_bps0 = []
    guided_bps1 = []
    raw_grads0 = []
    raw_grads1 = []
    raw_features = []
    grad_cam_nopools0 = []
    grad_cam_nopools1 = []
    grad_cam_orgs0 = []
    grad_cam_orgs1 = []
    flat_active_grads0 = []
    flat_active_grads1 = []
    flat_active_features = []
    
    labels = []
    predicted_labels = []
    predicted_probs = []

    bar = tqdm(total=data_size)
    
    for i in range(data_size):
        out = get_eeg_cam(
            model,
            dataset,
            device,
            i,
            args.kernel_size,
            level_size)


        guided_bp0, guided_bp1, \
        raw_grad0, raw_grad1, \
        raw_feature, \
        grad_cam_nopool0, grad_cam_nopool1, \
        grad_cam_org0, grad_cam_org1, \
        flat_active_grad0, flat_active_grad1, \
        flat_active_feature, \
        label, predicted_label, predicted_prob = out
        
        guided_bps0.append(guided_bp0)
        guided_bps1.append(guided_bp1)
        raw_grads0.append(raw_grad0)
        raw_grads1.append(raw_grad1)
        raw_features.append(raw_feature)
        grad_cam_nopools0.append(grad_cam_nopool0)
        grad_cam_nopools1.append(grad_cam_nopool1)
        grad_cam_orgs0.append(grad_cam_org0)
        grad_cam_orgs1.append(grad_cam_org1)
        flat_active_grads0.append(flat_active_grad0)
        flat_active_grads1.append(flat_active_grad1)
        flat_active_features.append(flat_active_feature)

        labels.append(label)
        predicted_labels.append(predicted_label)
        predicted_probs.append(predicted_prob)
        
        bar.update()
        
        if DEBUGGING and i == 3:
            break
        
    np_output_file_path = f"{output_dir}/cam_eeg_ct{classify_type}_{fold}"
    mat_output_file_path = f"{np_output_file_path}.mat"
    
    # Save in numpy format
    save_data = {
        'guided_bp0' : guided_bps0,
        'guided_bp1' : guided_bps1,
        'raw_grad0' : raw_grads0,
        'raw_grad1' : raw_grads1,
        'raw_feature' : raw_features,
        'cam_nopool0' : grad_cam_nopools0,
        'cam_nopool1' : grad_cam_nopools1,
        'cam0' : grad_cam_orgs0,
        'cam1' : grad_cam_orgs1,
        'flat_active_grad0' : flat_active_grads0,
        'flat_active_grad1' : flat_active_grads1,
        'flat_active_feature' : flat_active_features,
        'label' : labels,
        'predicted_label' : predicted_labels,
        'predicted_prob' : predicted_probs
    }
    
    np.savez_compressed(np_output_file_path, **save_data)
    scipy.io.savemat(mat_output_file_path, save_data)


def process_grad_cam_eeg():
    args = get_grad_cam_args()

    output_dir = args.save_dir + "/grad_cam/data"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for fold in range(args.fold_size):
        if args.classify_type == CLASSIFY_ALL or args.classify_type == FACE_OBJECT:
            process_grad_cam_eeg_sub(args,
                                     classify_type=FACE_OBJECT,
                                     fold=fold,
                                     output_dir=output_dir)

        if args.classify_type == CLASSIFY_ALL or args.classify_type == MALE_FEMALE:
            process_grad_cam_eeg_sub(args,
                                     classify_type=MALE_FEMALE,
                                     fold=fold,
                                     output_dir=output_dir)

        if args.classify_type == CLASSIFY_ALL or args.classify_type == ARTIFICIAL_NATURAL:
            process_grad_cam_eeg_sub(args,
                                     classify_type=ARTIFICIAL_NATURAL,
                                     fold=fold,
                                     output_dir=output_dir)


if __name__ == '__main__':
    process_grad_cam_eeg()
