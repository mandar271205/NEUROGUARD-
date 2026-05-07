# Third-Party Voice Stress Backbone

This folder holds the cloned upstream project:

```text
third_party/Stress-Detection-Through-Speech-Emotion-Recognition
```

NeuroGuard uses its `backbone_independent/` module as the preferred external baseline adapter for Windows/no-hardware speech stress detection.

Current limitation:

- The upstream GitHub repo includes code and an MIT license.
- It does not include trained `base_store/saved_models` or `base_store/saved_modelconfigs` artifacts.
- Until those artifacts are trained/copied in, NeuroGuard's `/predict/stress_voice` route uses a feature fallback for `stress_baseline`.

Expected artifact locations:

```text
backbone_independent/base_store/saved_models/{dataset}/{gender}/convolutional.h5
backbone_independent/base_store/saved_models/{dataset}/{gender}/convolutional.tflite
backbone_independent/base_store/saved_modelconfigs/{dataset}/{gender}/convolutional
```

Datasets:

```text
ravdess, cremad, emodb, shemo
```

Genders:

```text
female, male
```
