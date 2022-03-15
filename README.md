# Multi-modal deep neural decoding of visual object representation in humans

Getting started


## 1. Docker image build

```shell
$ cd dld
$ ./scripts/build.sh
```



## 2. Preprocessing

It must be performed the following steps for preprocessing when new experimental data are added or the preprocessing method is changed.



### 2.1 Update the Excel file controling experimental data 

Update and save as `dld/experiment_data/experiments.xlsx`

Save also in .csv format as `dld/experiment_data/experiments.csv`


In these Excel files, the experimental data must be formatted as follows. (Enter 0 for 'valid', if the data is not available.)

| valid| date | subject | run| reject_epoch|
| ------------- | ------------- | ------------- | ------------- | ------------- |
|1	|191008	|1	|1	|17,22,30,...|




### 2.2 Running Docker container

Run and enter Docker container.

Navigate to the project directory.

```
$ ./scripts/run.sh
# cd /opt/simul/
```



### 2.3 Data preprocessing

Convert Matlab and csv data to numpy format.

```shell
$ ./scripts/preprocess_alpha.sh
```




| Option | Description | Choices | Default |
| ------------- | ------------- | ------------- | ------------- |
| fmri | whether to preprocess the fmri data  | "true" "false"| "true" |
| eeg | whether to preprocess the eeg data  | "true" "false"| "true" |
| eeg_frame_type | frame type of the eeg data  | "normal", "filter", "ft"| "filter" |
| smooth | convert smoothed fmri data or non-smoothed data | "true" "false"| "true" |
| behavior  | whether to export a behavior data read from the csv data |"true" "false"| "true" |
| eeg_normalize_type | normalize type of the eeg data | "normal", "pre", "none" | "normal" |
| src_base | location of raw data files |  | "/data1/DLD/Data_Prepared" |
| dst_base | location of export files |  | "./data" |
| fmri_frame_type | frame type of the fmri data | "normal", "average", "three" | "normal" |

`--behavior` Regardless of this option, the behavior data is loaded from `experiments_data/experiemnts.csv` every time when the data preprocessing. `--behavior` option only specifies whether to save the loaded behavior data. 

 `--eeg`, `--fmri` options do conversion as preprocessing. #or# These options determine whether conversion is done.



The export files are written out to a determined subdirectory of `--dst_base`, depending on the combination specified in `--smooth` and `--fmri_frame_type` options, and `--eeg_normalize_type` and `--eeg_frame_type` options. For example, there is no need to separate directories for smoothing and non-smoothing; e.g., `/data2/Data_Converted_nosmoosth`. By placing the results of conversion of both smoothing and non-smoothing data, it is possible to switch which one is loaded by the optional arguments at Training. If all combinations of `--fmri_frame_type` and `--smooth` will be used for Training, it must be preprocessed for such all six combinations. The same applies to the combination of `--eeg_frame_type` and `--eeg_normalize_type`.



### 2.4 Trial-averaged data preprocessing

Trial-averaged data preprocessing must be done after the normal data preprocessing. For the trial-averaged data preprocessing, `--average_trial_size` and `--average_repeat_size` should be added to the same options as for the normal data preprocessing.

  (The Executable file should have all the same options as ### except for the following. It does not require the options of `--src_base` and `--behavior` unlike `preprocess_average.py`)

The same options of `--average_trial_size` and `--average_repeat_size` are used for later Training.



| Option | Description | Choices | Default |
| ------------- | ------------- | ------------- | ------------- |
| fmri | whether to preprocess the fmri data  | "true" "false"| "true" |
| eeg | whether to preprocess the eeg data  | "true" "false"| "true" |
| eeg_frame_type | frame type of the eeg data  | "normal", "filter", "ft"| "filter" |
| smooth | convert smoothed fmri data or non-smoothed data | "true" "false"| "true" |
| eeg_normalize_type | normalize type of the eeg data | "normal", "pre", "none" | "normal" |
| dst_base | location of raw data and export files |  | "./data" |
| fmri_frame_type | frame type of the fmri data | "normal", "average", "three" | "normal" |
| average_trial_size | average number of trials |  | 0 |
| average_repeat_size | number of repetitions for padding |  | 0 |



Example

```shell
python3 preprocess_average.py --dst_base=/data2/DLD/Data_Converted --eeg_frame_type=filter --average_trial_size=3 --average_repeat_size=4
```



## 3. Training

### 3.1 Running Docker container

```
$ ./scripts/run.sh
# cd /opt/simul/
```



### 3.2 Training EEG data

Example

```shell
python3 main_eeg.py --save_dir=./saved_eeg0 --data_dir=/data2/DLD/Data_Converted --model_type=tcn1 --test_subjects=TM_191008_01,TM_191009_01 --gpu=1
```

See below for options. (4.1.###)



### 3.3 Training fMRI data

Example

```shell
python3 main_fmri.py --save_dir=./saved_fmri0 --data_dir=/data2/DLD/Data_Converted --test_subjects=TM_191008_01,TM_191009_01 --gpu=1
```



### 3.4 Training Combined data

Example

```shell
python3 main_combined.py --save_dir=./saved_combined0 --data_dir=/data2/DLD/Data_Converted --model_type=combined_tcn1 --test_subjects=TM_191008_01,TM_191009_01 --preload_eeg_dir=./saved_eeg0 --preload_fmri_dir=./saved_fmri0 --gpu=1 --lr=0.001 --lr_eeg=0.001 --lr_fmri=0.01 --weight_decay=0.0 --weight_decay_eeg=0.0 --weight_decay_fmri=0.001
```



### 3.5 Test

The option of `--test=true` must be added for evaluation with test data.


Example

```shell
python3 main_eeg.py --save_dir=./saved_eeg0 --data_dir=/data2/DLD/Data_Converted --model_type=tcn1 --test_subjects=TM_191008_01,TM_191009_01 --gpu=1 --test=true

python3 main_fmri.py --save_dir=./saved_fmri0 --data_dir=/data2/DLD/Data_Converted --test_subjects=TM_191008_01,TM_191009_01 --test=true --gpu=1

python3 main_combined.py --save_dir=./saved_combined0 --data_dir=/data2/DLD/Data_Converted --model_type=combined_tcn1 --test_subjects=TM_191008_01,TM_191009_01 --preload_eeg_dir=./saved_eeg0 --preload_fmri_dir=./saved_fmri0 --test=true --gpu=1
```



### 3.6 Measures against Out out memory

If the memory of the first GPU is occupied by another processes, you may get the error `RuntimeError: CUDA error: out of memory` even when you specify the GPU option `--gpu=1`.

In such a case, the problem can be solved setting the environment variable `export export CUDA_VISIBLE_DEVICES=1` and specifying `--gpu=0`.

(The program will recognize the second GPU as the first one.)


```shell
$ export CUDA_VISIBLE_DEVICES=1
$ python3 main_combined.py --save_dir=./saved_combined0 --data_dir=/data2/DLD/Data_Converted --model_type=combined_filter1 --test_subjects=TM_191008_01,TM_191009_01 --preload_eeg_dir=./saved_eeg0 --preload_fmri_dir=./saved_fmri0 --gpu=0
```



### 3.7 Model type

The arguments implemented in the `model_type` option are as follows.


#### EEG

| model_type | Model name | Description |
| :--------- | ------------------ | ---- |
| model1     | EEGModel           | 1D Conv model |
| model2     | EEGModel2          | a model with a larger stride on the first layer of EEGModel |
| rnn1       | EEGRNNModel        | RNN(LSTM) model |
| convrnn1   | EEGConvRNNModel    | a model with 1D Conv followed by LSTM applied |
| filter1    | EEGFilterModel     | a filter model with 2D convolution: the input data is considered as an image of width:250, height:63, and color:5ch |
| filter2    | EEGFilterModel2    | a filter model with 2D convolution: the input data is considered as an image of width:250, height:5, and color:63ch |
| filter3    | EEGFilterModel3    | a filter model with the first connection layer followed by 1D Conv applied |
| ft1        | EEGFtModel         | a model compatible with FT Spectrogram |
| stnn1      | EEGSTNNModel       | STNN model |
| tcn1      | EEGSTCNModel       | TCN model: use only the last step |
| tcn2      | EEGSTCNModel2       | TCN model: use all steps |

#### fMRI

| model_type | Model name | Description |
| :--------- | ------------------ | ---- |
|            | FMRIModel          | 3D Conv model |

#### Combined

| model_type | Model name | Description |
| :--------- | -------- | ---- |
| combined1     | CombinedModel | a combined model compatible with FMRIModel and EEGModel(`model1`) |
| combined_filter1     |  CombinedFilterModel   | a filter model compatible with FMRIModel and EEGFilterModel2(`model2`) |
| combined_tcn1     |  CombinedTCNModel   | a model compatible with FMRIModel and EEGTCNModel(`tcn1`) |




## 4. Training parameters

See `dld/options.py` for details.



### 4.1 Options common to EEG/fMRI/Combined

| Option | Description | Choices | Default |
| ------------- | ------------- | ------------- | ------------- |
| data_seed | a random seed used for Cross-Validation separation (basically unchanged) | | 0 |
| run_seed | to fix a seed (not using a random seed), enter a specific number other than -1. (takes longer) | | -1 |
| save_dir  | save directory  | | "saved" |
| classify_type  | classification type/stimulus condition | 0=FACE/PLACE 1=MALE/FEMALE, 2=ARTIFICAL/NATURAL, -1=ALL| -1 |
| desc  | experiment descriptions | | |
| early_stopping| whether to use Early Stopping |  "true"/"false" | "true" |
| parallel| whether to train on multiple GPUs |  "true"/"false" | "false" |
| data_dir | directory of experimental data | |  "./data" |
| eeg_normalize_type| normalize type of the eeg data　(normal=normal, pre=use the data from the period before fixations, none=no normalization) |  "normal", "pre", "none" | "normal" |
| fmri_frame_type| frame type of the fmri data (normal=normal, average=use the average data of 3TR, three=use the all data of 3TR) |  "normal", "avarage", "three" | "normal" |
| gpu | specify the GPU to use (-1=unspecified, 0=first GPU, 1=second GPU) | | -1 |
| eeg_frame_type | frame type of the eeg data (normal=normal, filter=5ch filter, ft=FT spectorogram) | "normal", "filter", "ft" | "filter" |
| smooth | whether to use smoothed fmri data | "true"/"false" | "true" |
| test_subjects | specify participants to be used for the test | enter the participants' IDs, separated by commas | "TM_191008_01,TM_191009_01" |
| test | whether to be test or not | "true"/"false" | "false" |
| fold_size | number of Fold to be used out of 10 Fold |  | 10 |
| subjects_per_fold | number of participants assined to 1 Fold |  | 4 |
| patience | number of continuous epochs in Early Stopping |  | 20 |
| batch_size | batch size | | 10 |
| lr | learning rate | | 0.001 |
| weight_decay | regularization parameter weight_decay | | 0.0 |
| epochs | number of training epochs | | 100 |
| average_trial_size | average number of trials |  | 0 |
| average_repeat_size | number of repetitions for padding |  | 0 |
| kernel_size | kernel size (available in STNN and TCN) |  | 3 |
| level_size | number of TemporalBlock (available in TCN) (-1=automatically calculated) |  | -1 |
| level_hidden_size | number of channels of TemporalBlock (available in TCN) (63=residual become skip connection) |  | 63 |
| residual | whether to use residual connection (available in TCN) | "true"/"false" | "true" |



### 4.2 Options only for main_eeg.py runtime

| Option | Description | Choices | Default |
| ------------- | ------------- | ------------- | ------------- |
| model_type  | model type  | "model1", "model1", "rnn1", "convrnn1", "filter1", "filter2", "filter3", "stnn1", "tcn1", "tcn2"| "model1"|



### 4.3 Options only for main_combined.py runtime

| Option | Description | Choices | Default |
| ------------- | ------------- | ------------- | ------------- |
| fix_preloads | whether to retrain the weights of the preloaded EEG/fMRI model | "true" "false"| "true" |
| preload_eeg_dir |  path to the preloaded EEG model | | unspecified |
| preload_fmri_dir |  path to the preloaded fMRI model | | unspecified |
| lr_eeg | learning rate of the EEG model | | unspecified |
| lr_fmri |  learning rate of the fMRI model | | unspecified |
| weight_decay_eeg | weight decay of the EEG model | | unspecified |
| weight_decay_fmri |  weight decay of the fMRI model | | unspecified |
| model_type  | model type  | "combined1", "combined_filter1", "combined_tcn1"| "combined_tcn1" |
| combined_hidden_size  | hidden size of Combined FC part | | 128 |
| combined_layer_size  | additional layer size of Combined FC part | | 0 |


`lr` specify the learning rate for the last FC part. `lr_eeg` and `lr_fmri` specify the learning rate for the EEG and fMRI part.
`weight_decay` specify the weight decay for the last FC part. `weight_decay_eeg` and `weight_decay_fmri` specify the weight decay for the EEG and fMRI part.

If `lr_eeg` and/or `lr_fmri` are not specified, `lr` is applied instead. `weight_decay` is same manner.


If either `preload_eeg_dir` or `preload_frmi_dir` is not specified, both EEG and fMRI model are not preloaded. (Only one side is not acceptable)


Specifying `combined_hidden_size` and `combined_layer_size` can increase the additional Full Connection layer that is combined by EEG and fMRI layer.
To keep it the same as so far, input `combined_hidden_size=128` and `combined_layer_size=0`.



## 6. Visualization of Grad-CAM

Output data and visualize the results as follows.



Example

```shell
python3 main_grad_cam_eeg.py --save_dir=./saved_eeg0 --data_dir=/data2/DLD/Data_Converted --model_type=tcn1 --test_subjects=TM_191008_01,TM_191009_01 --gpu=1 --test=true

python3 main_grad_cam_fmri.py --save_dir=./saved_fmri0 --data_dir=/data2/DLD/Data_Converted --test_subjects=TM_191008_01,TM_191009_01 --gpu=1 --test=true
```

The options for computing Grad-CAM are same as those for **test** except for `run_seed`, `classify_type`, `early_stopping`, `parallel`, `patience`,and `batch_size`. 
Moreover, `preload_eeg_dir` and `preload_fmri_dir` are eliminated for running `main_grad_cam_combined`, unlike in training.



| Option | Description | Choices | Default |
| ------------- | ------------- | ------------- | ------------- |
| data_dir  | data directory | | "./data" |
| save_dir  | output directory of model data and results | | "saved" |
| classify_type  | classification type/stimulus condition  | 0=FACE/PLACE 1=MALE/FEMALE, 2=ARTIFICAL/NATURAL, -1=ALL| -1 |
| eeg_normalize_type| normalize type of the eeg data　(normal=normal, pre=use the data from the period before fixations, none=no normalization) |  "normal", "pre", "none" | "normal" |
| fmri_frame_type| frame type of the fmri data (normal=normal, average=use the average data of 3TR, three=use the all data of 3TR) |  "normal", "avarage", "three" | "normal" |
| model_type  | model type  | specify the same model_type as Training | specify the same model_type as Training |
| eeg_frame_type | frame type of the eeg data (normal=normal, filter=5ch filter, ft=FT spectorogram) | "normal", "filter", "ft" | "filter" |
| smooth | whether to use smoothed fmri data | "true"/"false" | "true" |
| gpu | specify the GPU to use (-1=unspecified, 0=first GPU, 1=second GPU) | | -1 |
| data_seed | a random seed used for Cross-Validation separation (basically unchanged) | | 0 |
| test | whether to use the test data set (false=use the validation data set) | "true"/"false" | "true" |
| test_subjects | specify participants to be used for the test | enter the participants' IDs, separated by commas | "TM_191008_01,TM_191009_01" |
| fold_size | number of Fold to be used out of 10 Fold |  | 10 |
| subjects_per_fold | number of participants assined to 1 Fold |  | 4 |
| kernel_size | kernel size (available in STNN and TCN) |  | 3 |
| level_size | number of num_channels (available in TCN) (-1=automatically calculated) |  | -1 |
| level_hidden_size | number of channels of num_channels (available in TCN) |  | 63 |
| residual | whether to use residual connection (available in TCN) | "true"/"false" | "true" |



### Grad-CAMデータ形式

`save_dir`で指定したディレクトリ以下の、`grad_cam/data`以下に、numpy形式とmatlab形式の両方で書き出される.



#### EEG

| Key名 | Description |　Shape |
| ------------------ | ------------- | ------------- |
| guided_bp0         | Guided-Backpropの結果, label=0に対する結果 | (*, 63, 250) |
| guided_bp1         | Guided-Backpropの結果, label=1に対する結果 | (*, 63, 250) |
| cam_nopool0        | 各LevelでのGrad-CAM(poolingなし), label=0に対する結果 | (*, 7, 250) |
| cam_nopool1        | 各LevelでのGrad-CAM(poolingなし), label=1に対する結果 | (*, 7, 250) |
| cam0               | 各LevelでのGrad-CAM(pooling有り), label=0に対する結果 | (*, 7, 250) |
| cam1               | 各LevelでのGrad-CAM(pooling有り), label=1に対する結果 | (*, 7, 250) |
| raw_grad0          | 各Levelでの(有効位置を考慮しない生の)勾配, label=0に対する結果 | (*, 7, 63, 250) |
| raw_grad1          | 各Levelでの(有効位置を考慮しない生の)勾配, label=1に対する結果 | (*, 7, 63, 250) |
| raw_feature        | 各Levelでの(有効位置を考慮しない生の)Activation        | (*, 7, 63, 250) |
| flat_active_grad0  | 各Levelでのdilated convでの有効位置のみを抜き出した勾配, level=0に対する結果 | (*, 7, []) |
| flat_active_grad1  | 各Levelでのdilated convでの有効位置のみを抜き出した勾配, level=1に対する結果 | (*, 7, []) |
| flat_active_feature| 各Levelでのdilated convでの有効位置のみを抜き出したActivation | (*, 7, []) |
| label              | 正解ラベル (0 or 1) | (1, *) |
| predicted_label    | 予測ラベル (predicted_prob > 0.5なら1, そうでなければ0) | (1, *) |
| predicted_prob     | 予測確率 (0.0~1.0) | (1, *) |

(※リスト内の`7` の部分は`kernel_size=2` の場合の例で、`kernel_size` を変えると値は変わる)

Guided-Grad-CAMを算出するには、`cam_nopool0 * guided_bp0` もしくは `cam_nopool1 * guided_bp1` を利用する.
`cam_nopool0`, `cam_nopool1`, `cam0`, `cam1`は、`flat_active_grad0`, `flat_active_grad1`, `flat_active_feature` の値を元に算出したgradient x activationの値を250frame分になる様に補完をしたものである.

`flat_active_grad0`, `flat_active_grad1`, `flat_active_feature` は各Levelにおいて要素数が異なるが、その異なる要素数を1つのarrayに収めるために1次元の配列にflat化している. 例えば、kernel_size=2の場合、Level数は7になるが、acvtiveなgradient (有効なgradient)は各Levelにおいて `(63, 250), (63, 125), (63, 63), (63, 31), (63, 15), (63, 7), (63, 3)` となるが、それをflat化した1次元の配列 `(15750), (7875), (3969), (1953), (945), (441), (189)` として保持している.  `flat_active_*` は確認用で、実際の可視化にはそれらをもとに処理をした`cam_nopool*`や、`cam*`を利用することを想定している.



#### fMRI


| Key名 | Description |　Shape |
| ------------------ | ------------- | ------------- |
| cam0               | Global-Pooling利用, 最終層Grad-CAM, label=0に対する結果 | (*, 6, 7, 6)  |
| cam1               | Global-Pooling利用, 最終層Grad-CAM, label=1に対する結果 | (*, 6, 7, 6)  |
| cam_nopool0        | Global-Pooling利用しない, 最終層Grad-CAM, label=0に対する結果 | (*, 6, 7, 6) |
| cam_nopool1        | Global-Pooling利用しない, 最終層Grad-CAM, label=1に対する結果 | (*, 6, 7, 6) |
| guided_bp0         | Guided-Backpropの結果, label=0に対する結果 | (*, 79, 95, 79) |
| guided_bp1         | Guided-Backpropの結果, label=1に対する結果 | (*, 79, 95, 79) |
| guided_cam_nopool0 | Global-Pooling利用しない, Guided-GradCAMの結果, label=0に対する結果 | (*, 79, 95, 79) |
| guided_cam_nopool1 | Global-Pooling利用しない, Guided-GradCAMの結果, label=1に対する結果 | (*, 79, 95, 79) |
| label              | 正解ラベル (0 or 1) | (1, *) |
| predicted_label    | 予測ラベル (predicted_prob > 0.5なら1, そうでなければ0) | (1, *) |
| predicted_prob     | 予測確率 (0.0~1.0) | (1, *) |

`label`が1で`predicted_label`が1の場合は予測が正しかった場合であり、その時`guided_cam_nopool1が(正解である)ラベル1を予測した時のGuided-Grad-CAMの結果となる.
`

`label`が1で`predicted_label`が0の場合は、予測が外れたことを示す.



## 8. Grid search

グリッドサーチを行うには、`main_grid_search_example.py` を参考にしてグリッドサーチ用のスクリプトを用意して実行する.


スクリプトには以下の様に、実行ファイル、保存ディレクトリ名prefix, グリッドサーチ対象オプション、固定オプションを指定する.

```python
#-----[変更箇所 ここから]-----
# 実行するファイル名を指定
target_file = "main_eeg.py"

save_dir_prefix = "./saved_eeg"
# 保存ディレクトリは、"./saved_eeg_0_0", "./saved_eeg_0_1" ... などとなる.

# グリッドサーチ対象オプション
# 対処のオプションを配列で指定する
variable_options["lr"]           = ["0.1", "0.01", "0.001"]
variable_options["weight_decay"] = ["0.0", "0.01", "0.1"]

# 固定オプション
fixed_options["data_dir"]      = "./data2/DLD/Data_Converted"
fixed_options["model_type"]    = "filter2"
fixed_options["test_subjects"] = "TM_191008_01,TM_191009_01"
fixed_options["fold_size"]     = "1" # 1Foldのみを対象にして高速化する場合
#-----[変更箇所 ここまで]-----
```



サンプルと同様なスクリプトを用意して実行する.

```shell
python3 main_grid_search_sample.py
```



上記の例だと実行後に、`./saved_eeg_summary/summary.tx`に以下に様にサマリが出力される.
 (varidationのスコアが一番よかったものに**best**という表示がされる.)

```
[ClasslfyType0]
  [    ] ./saved_eeg_0_0: 50.0 (lr=0.1 weight_decay=0.0)
  [    ] ./saved_eeg_0_1: 50.0 (lr=0.1 weight_decay=0.01)
  [    ] ./saved_eeg_0_2: 50.0 (lr=0.1 weight_decay=0.1)
  [    ] ./saved_eeg_1_0: 50.0 (lr=0.01 weight_decay=0.0)
  [    ] ./saved_eeg_1_1: 50.0 (lr=0.01 weight_decay=0.01)
  [    ] ./saved_eeg_1_2: 50.0 (lr=0.01 weight_decay=0.1)
  [    ] ./saved_eeg_2_0: 50.0 (lr=0.001 weight_decay=0.0)
  [best] ./saved_eeg_2_1: 63.333333333333333 (lr=0.001 weight_decay=0.01)
  [    ] ./saved_eeg_2_2: 50.0 (lr=0.001 weight_decay=0.1)

[ClasslfyType1]
  [best] ./saved_eeg_0_0: 53.333333333333336 (lr=0.1 weight_decay=0.0)
  [    ] ./saved_eeg_0_1: 53.333333333333336 (lr=0.1 weight_decay=0.01)
  [    ] ./saved_eeg_0_2: 46.666666666666664 (lr=0.1 weight_decay=0.1)
...以下略  
```

