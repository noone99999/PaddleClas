# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import sys

__dir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(__dir__, '../')))

import cv2
import numpy as np

from utils import logger
from utils import config
from utils.predictor import Predictor
from utils.get_image_list import get_image_list
from preprocess import create_operators
from postprocess import build_postprocess


class RecPredictor(Predictor):
    def __init__(self, config):
        super().__init__(config["Global"],
                         config["Global"]["rec_inference_model_dir"])
        self.preprocess_ops = create_operators(config["RecPreProcess"][
            "transform_ops"])
        self.postprocess = build_postprocess(config["RecPostProcess"])

    def predict(self, images, feature_normalize=False):
        input_names = self.paddle_predictor.get_input_names()
        input_tensor = self.paddle_predictor.get_input_handle(input_names[0])

        output_names = self.paddle_predictor.get_output_names()
        output_tensor = self.paddle_predictor.get_output_handle(output_names[
            0])

        if not isinstance(images, (list, )):
            images = [images]
        for idx in range(len(images)):
            for ops in self.preprocess_ops:
                images[idx] = ops(images[idx])
        image = np.array(images)

        input_tensor.copy_from_cpu(image)
        self.paddle_predictor.run()
        batch_output = output_tensor.copy_to_cpu()
        
        if feature_normalize:
            feas_norm = np.sqrt(
                np.sum(np.square(batch_output), axis=1, keepdims=True))
            batch_output = np.divide(batch_output, feas_norm)
            
        return batch_output


def main(config):
    rec_predictor = RecPredictor(config)
    image_list = get_image_list(config["Global"]["infer_imgs"])

    assert config["Global"]["batch_size"] == 1
    for idx, image_file in enumerate(image_list):
        batch_input = []
        img = cv2.imread(image_file)[:, :, ::-1]
        output = rec_predictor.predict(img)
        if rec_predictor.postprocess is not None:
            output = rec_predictor.postprocess(output)
        print(output.shape)
    return


if __name__ == "__main__":
    args = config.parse_args()
    config = config.get_config(args.config, overrides=args.override, show=True)
    main(config)
