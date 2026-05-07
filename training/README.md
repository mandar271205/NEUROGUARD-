# Option B: SenseVoice Teacher + NeuroGuard Student

Option B is the selected NeuroGuard v2 training strategy.

```text
SenseVoiceSmall teacher, offline only
        |
        v
soft SER guidance
        |
        v
NeuroGuard student model + z-vector personalization
        |
        v
deployed stress model
```

## Why Option B Is Okay

- The external model is not the production decision-maker.
- The teacher is frozen and used only during training.
- Runtime inference uses only the NeuroGuard student model.
- Personalization stays in NeuroGuard through the enrolment `z_vector`.
- Same audio can still produce different scores for different students because the final head is conditioned by each student's `z_vector`.

## Install

```powershell
pip install -r training/requirements.txt
```

## Train

Create real `.wav` files that match `data_factory/manifest.csv`, then run:

```powershell
python -m training.train_distillation --manifest data_factory/manifest.csv
```

For a quick code-path check without downloading SenseVoice:

```powershell
python -m training.train_distillation --manifest data_factory/manifest.csv --disable-teacher
```

## Loss

```text
loss = (1 - alpha) * CE(student, stress_label)
     + alpha * KL(student / T, teacher / T)
```

Default values:

- `alpha = 0.7`
- `temperature = 2.0`

## Important License Note

Use `FunAudioLLM/SenseVoiceSmall` as the SER teacher candidate and validate its license for your final deployment context. Do not use `nvidia/Audio2Emotion-v3.0` for this app because its license prohibits standalone emotion-recognition use outside Audio2Face.
