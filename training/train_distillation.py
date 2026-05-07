from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from tqdm import tqdm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Option B: SenseVoice -> NeuroGuard distillation.")
    parser.add_argument("--manifest", default="data_factory/manifest.csv")
    parser.add_argument("--out", default="backend/models/neuroguard_audio_student.pt")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--alpha", type=float, default=0.7)
    parser.add_argument("--temperature", type=float, default=2.0)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--teacher-device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--teacher-model", default="FunAudioLLM/SenseVoiceSmall")
    parser.add_argument("--disable-teacher", action="store_true")
    return parser.parse_args()


def train() -> None:
    args = parse_args()
    from training.dataset import SpeechManifestDataset, collate_speech_batch
    from training.distillation_loss import distillation_loss
    from training.student_model import NeuroGuardStudent
    from training.teacher_sensevoice import SenseVoiceTeacher

    dataset = SpeechManifestDataset(args.manifest)
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_speech_batch,
    )

    student = NeuroGuardStudent().to(args.device)
    teacher = SenseVoiceTeacher(
        model_dir=args.teacher_model,
        device=args.teacher_device,
        enabled=not args.disable_teacher,
    )
    optimizer = torch.optim.AdamW(student.parameters(), lr=args.lr, weight_decay=1e-4)

    for epoch in range(1, args.epochs + 1):
        student.train()
        running = {"loss": 0.0, "loss_ce": 0.0, "loss_kd": 0.0}
        progress = tqdm(loader, desc=f"epoch {epoch}/{args.epochs}")
        for batch in progress:
            log_mel = batch["log_mel"].to(args.device)
            labels = batch["labels"].to(args.device)

            with torch.no_grad():
                logits_teacher = teacher.predict_batch(batch["audio_paths"]).to(args.device)

            logits_student = student(log_mel)
            loss, metrics = distillation_loss(
                logits_student=logits_student,
                logits_teacher=logits_teacher,
                labels=labels,
                alpha=args.alpha,
                temperature=args.temperature,
            )

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()

            for key in running:
                running[key] += metrics[key]
            progress.set_postfix({key: f"{metrics[key]:.4f}" for key in metrics})

        steps = max(len(loader), 1)
        print(
            f"epoch={epoch} "
            f"loss={running['loss'] / steps:.4f} "
            f"ce={running['loss_ce'] / steps:.4f} "
            f"kd={running['loss_kd'] / steps:.4f}"
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": student.state_dict(),
            "model_config": {
                "n_mels": 64,
                "hidden_dim": 128,
                "z_dim": 48,
                "class_count": 3,
            },
            "distillation": {
                "teacher_model": args.teacher_model,
                "alpha": args.alpha,
                "temperature": args.temperature,
            },
        },
        out_path,
    )
    print(f"saved={out_path}")


if __name__ == "__main__":
    train()
