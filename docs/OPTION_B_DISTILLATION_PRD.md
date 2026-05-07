# Section 5: Option B - Knowledge Distillation With NeuroGuard Student Model

## Decision

Yes, Option B is okay to use for NeuroGuard v2. It is the preferred approach because the external model is used only as an offline teacher during training, while the final deployed stress detector remains the NeuroGuard model.

```text
SenseVoiceSmall teacher
        ↓
soft SER guidance during training
        ↓
NeuroGuard student model + z_vector personalization
        ↓
deployed personalized stress score
```

## 5.1 Teacher Model: SenseVoiceSmall

- Model: `FunAudioLLM/SenseVoiceSmall`
- Role: frozen offline speech-emotion teacher.
- Use: generate emotion-style soft targets for training.
- Runtime: not used in FastAPI inference.

SenseVoiceSmall supports speech understanding tasks including ASR, language identification, speech emotion recognition, and audio event detection. For Hinglish or Indian-student speech, treat it as a strong transfer teacher and validate on local student voice samples.

Source: https://huggingface.co/FunAudioLLM/SenseVoiceSmall

## 5.2 Student Model: NeuroGuard

```text
Raw audio
  ↓
Audio feature backbone
  ↓
Enrolment encoder
  ↓
z_vector per student
  ↓
Personalized stress head
  ↓
stress_score
```

The deployed model is still NeuroGuard. The teacher improves representation learning, but the final stress decision is made by the student model.

## 5.3 Loss Function

Training uses hard stress labels plus teacher soft targets:

```python
loss = (1 - alpha) * cross_entropy(student_logits, labels)
loss += alpha * kl_divergence(student_logits / temperature, teacher_logits / temperature)
```

Recommended defaults:

- `alpha = 0.7`
- `temperature = 2.0`

## 5.4 Inference

At inference time:

```python
stress_score = neuroguard_model(audio, z_vector)
```

No SenseVoice call happens during serving. This keeps the app faster, cheaper, and more private.

## 5.5 Why Same Audio Can Give Different Student Scores

```text
same audio + student A z_vector -> stress_score A
same audio + student B z_vector -> stress_score B
```

The teacher gives general emotion knowledge. The personalized NeuroGuard head uses each student's enrolment vector to produce the final score.

## 5.6 License Safety

Do not use `nvidia/Audio2Emotion-v3.0` for this app. Its license prohibits use for standalone emotion recognition outside Audio2Face.

Source: https://huggingface.co/nvidia/Audio2Emotion-v3.0/blob/main/LICENSE

For SenseVoiceSmall, do a final license review before any commercial deployment. For academic/demo work, this Option B architecture is acceptable.

## 5.7 Repo Implementation

Implemented files:

- `training/teacher_sensevoice.py`
- `training/student_model.py`
- `training/dataset.py`
- `training/distillation_loss.py`
- `training/train_distillation.py`

Run:

```powershell
pip install -r training/requirements.txt
python -m training.train_distillation --manifest data_factory/manifest.csv
```

Quick check without downloading SenseVoice:

```powershell
python -m training.train_distillation --manifest data_factory/manifest.csv --disable-teacher
```
