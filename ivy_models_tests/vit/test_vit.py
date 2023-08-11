import os
import numpy as np
import pytest
import random
import ivy
from ivy_models_tests import helpers
from ivy_models.vit import (
    vit_b_16,
    vit_b_32,
    vit_h_14,
    vit_l_16,
    vit_l_32,
)


VARIANTS = {
    "vit_b_16": vit_b_16,
    "vit_b_32": vit_b_32,
    # "vit_h_14": vit_h_14,
    "vit_l_16": vit_l_16,
    "vit_l_32": vit_l_32,
}


load_weights = random.choice([False, True])
model_var = random.choice(list(VARIANTS.keys()))
model = VARIANTS[model_var](pretrained=load_weights)
v = ivy.to_numpy(model.v)


@pytest.mark.parametrize("data_format", ["NHWC", "NCHW"])
def test_vit_img_classification(device, fw, data_format):
    """Test ViT image classification."""
    num_classes = 1000
    batch_shape = [1]
    this_dir = os.path.dirname(os.path.realpath(__file__))

    # Load image
    img = ivy.asarray(
        helpers.load_and_preprocess_img(
            os.path.join(this_dir, "..", "..", "images", "cat.jpg"),
            256,
            224,
            data_format="NHWC",
            to_ivy=True,
        ),
    )

    # Create model
    model.v = ivy.asarray(v)
    logits = model(img, data_format="NHWC")

    # Cardinality test
    assert logits.shape == tuple([ivy.to_scalar(batch_shape), num_classes])

    # Value test
    if load_weights:
        np_out = ivy.to_numpy(logits[0])
        true_indices = np.sort(np.array([282, 281, 285, 287, 292]))
        calc_indices = np.sort(np.argsort(np_out)[-5:][::-1])
        assert np.array_equal(true_indices, calc_indices)
