# global
import ivy
import torch


def _prune_keys(raw, ref, raw_keys_to_prune=[], ref_keys_to_prune=[]):
    pruned_ref = []
    if raw_keys_to_prune:
        raw = raw.cont_prune_keys(raw_keys_to_prune)
    if ref_keys_to_prune:
        pruned_ref.append(ref.cont_at_keys(ref_keys_to_prune))
        ref = ref.cont_prune_keys(ref_keys_to_prune)
    return raw, ref, pruned_ref


def _map_weights(raw, ref, custom_mapping=None):
    mapping = {}
    for old_key, new_key in zip(
        raw.cont_sort_by_key().cont_to_iterator_keys(),
        ref.cont_sort_by_key().cont_to_iterator_keys(),
    ):
        new_mapping = new_key
        if custom_mapping is not None:
            new_mapping = custom_mapping(old_key, new_key)
            if new_mapping is None:
                continue
        mapping[old_key] = new_mapping
    return mapping


def load_torch_weights(
    url,
    ref_model,
    raw_keys_to_prune=[],
    ref_keys_to_prune=[],
    custom_mapping=None,
    map_location=torch.device("cpu"),
):
    ivy.set_backend("torch")
    weights = torch.hub.load_state_dict_from_url(url, map_location=map_location)

    weights_raw = ivy.to_numpy(ivy.Container(weights))
    weights_raw, weights_ref = _prune_keys(
        weights_raw, ref_model.v, raw_keys_to_prune, ref_keys_to_prune
    )
    mapping = _map_weights(weights_raw, weights_ref, custom_mapping=custom_mapping)

    ivy.previous_backend()
    w_clean = weights_raw.cont_restructure(mapping, keep_orig=False)
    return ivy.asarray(w_clean)


def _rename_weights(raw, ref, rename_dict):
    renamed_ref = []
    for raw_key, ref_key in rename_dict.items():
        old_v = raw.cont_at_keys(raw_key)
        new_v = ref.cont_at_keys(ref_key)
        mapping = {}
        for old_key, new_key in zip(
            old_v.cont_sort_by_key().cont_to_iterator_keys(),
            new_v.cont_sort_by_key().cont_to_iterator_keys(),
        ):
            mapping[old_key] = new_key

        renamed_ref.append(old_v.cont_restructure(mapping, keep_orig=False))
        raw = raw.cont_prune_keys(raw_key)
        ref = ref.cont_prune_keys(ref_key)
    return raw, ref, renamed_ref


def load_jax_weights(
    url,
    ref_model,
    custom_mapping=None,
    raw_keys_to_prune=[],
    ref_keys_to_prune=[],
    special_rename={},
):
    import pickle

    ivy.set_backend("jax")
    # todo: refactor this into a url load helper
    # urllib.request.urlretrieve(url, filename="jax_weights.pystate")
    with open("jax_weights.pystate", "rb") as f:
        weights = pickle.loads(f.read())
    # os.remove("jax_weights.pystate")

    try:
        weights = {**weights["params"], **weights["state"]}
    except KeyError:
        pass

    weights_raw = ivy.to_numpy(ivy.Container(weights))
    # print(ivy.asarray(ivy.Container(weights)))
    # return
    weights_ref = ref_model.v
    # print(weights_ref)
    # return
    weights_raw, weights_ref, pruned_ref = _prune_keys(
        weights_raw, weights_ref, raw_keys_to_prune, ref_keys_to_prune
    )

    if special_rename:
        weights_raw, weights_ref, renamed_ref = _rename_weights(
            weights_raw, weights_ref, special_rename
        )
    mapping = _map_weights(weights_raw, weights_ref, custom_mapping=custom_mapping)

    ivy.previous_backend()
    print(mapping)
    w_clean = weights_raw.cont_restructure(mapping, keep_orig=False)

    if special_rename:
        w_clean = ivy.Container.cont_combine(w_clean, *renamed_ref)
    if ref_keys_to_prune:
        w_clean = ivy.Container.cont_combine(w_clean, *pruned_ref)
    return ivy.asarray(w_clean)
