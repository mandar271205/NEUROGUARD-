from __future__ import annotations

import torch
import torch.nn.functional as F


def distillation_loss(
    logits_student: torch.Tensor,
    logits_teacher: torch.Tensor,
    labels: torch.Tensor,
    alpha: float = 0.7,
    temperature: float = 2.0,
) -> tuple[torch.Tensor, dict[str, float]]:
    loss_ce = F.cross_entropy(logits_student, labels)
    teacher_probs = F.softmax(logits_teacher / temperature, dim=-1)
    student_log_probs = F.log_softmax(logits_student / temperature, dim=-1)
    loss_kd = F.kl_div(
        student_log_probs,
        teacher_probs,
        reduction="batchmean",
    ) * (temperature**2)
    loss = (1.0 - alpha) * loss_ce + alpha * loss_kd
    return loss, {
        "loss": float(loss.detach().cpu()),
        "loss_ce": float(loss_ce.detach().cpu()),
        "loss_kd": float(loss_kd.detach().cpu()),
    }
