from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import zipfile
from pathlib import Path


DATASETS = (
    "ravdess_f",
    "ravdess_m",
    "cremad_f",
    "cremad_m",
    "emodb_f",
    "emodb_m",
    "shemo_f",
    "shemo_m",
)


def ensure_dirs(clean_audio: Path) -> None:
    for dataset in DATASETS:
        (clean_audio / dataset).mkdir(parents=True, exist_ok=True)


def copy_file(src: Path, dest: Path) -> bool:
    if not src.exists() or not src.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size == src.stat().st_size:
        return False
    shutil.copy2(src, dest)
    return True


def organize_ravdess(resources: Path, clean_audio: Path) -> int:
    source = resources / "RAVDESS_Audio"
    copied = 0
    for wav in source.glob("Actor_*/*.wav"):
        actor = int(wav.stem.split("-")[-1])
        gender_dir = "ravdess_f" if actor % 2 == 0 else "ravdess_m"
        copied += copy_file(wav, clean_audio / gender_dir / wav.name)
    return copied


def load_cremad_gender_map(cremad_root: Path) -> dict[str, str]:
    csv_path = cremad_root / "VideoDemographics.csv"
    mapping: dict[str, str] = {}
    if not csv_path.exists():
        return mapping
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            actor = (row.get("ActorID") or row.get("ActorId") or row.get("actor_id") or "").strip()
            sex = (row.get("Sex") or row.get("Gender") or "").strip().lower()
            if actor:
                mapping[actor] = "female" if sex.startswith("f") else "male"
    return mapping


def organize_cremad(resources: Path, clean_audio: Path) -> int:
    root = resources / "CREMA-D"
    audio = ensure_cremad_wav(root)
    genders = load_cremad_gender_map(root)
    copied = 0
    for wav in audio.glob("*.wav"):
        actor = wav.stem.split("_")[0]
        gender = genders.get(actor)
        if gender not in {"female", "male"}:
            continue
        dataset = "cremad_f" if gender == "female" else "cremad_m"
        copied += copy_file(wav, clean_audio / dataset / wav.name)
    return copied


def ensure_cremad_wav(root: Path) -> Path:
    wav_dir = root / "AudioWAV"
    mp3_dir = root / "AudioMP3"
    wav_dir.mkdir(parents=True, exist_ok=True)
    if not mp3_dir.exists():
        return wav_dir

    try:
        import imageio_ffmpeg
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("imageio-ffmpeg is required to convert CREMA-D MP3 files to WAV") from exc

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    mp3_files = list(mp3_dir.glob("*.mp3"))
    for index, mp3 in enumerate(mp3_files, start=1):
        wav = wav_dir / f"{mp3.stem}.wav"
        if wav.exists() and wav.stat().st_size > 0:
            continue
        if index % 250 == 0:
            print(f"  converting CREMA-D MP3 -> WAV: {index}/{len(mp3_files)}")
        subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(mp3),
                "-acodec",
                "pcm_s16le",
                str(wav),
            ],
            check=True,
        )
    return wav_dir


def organize_emodb(resources: Path, clean_audio: Path) -> int:
    source = resources / "EmoDB" / "wav"
    male_speakers = {"03", "10", "11", "12", "15"}
    female_speakers = {"08", "09", "13", "14", "16"}
    copied = 0
    for wav in source.glob("*.wav"):
        speaker = wav.stem[:2]
        if speaker in male_speakers:
            dataset = "emodb_m"
        elif speaker in female_speakers:
            dataset = "emodb_f"
        else:
            continue
        copied += copy_file(wav, clean_audio / dataset / wav.name)
    return copied


def organize_shemo(resources: Path, clean_audio: Path) -> int:
    source = resources / "ShEMO"
    ensure_shemo_extracted(source)
    copied = 0
    for wav in source.rglob("*.wav"):
        first = wav.name[:1].upper()
        if first == "F":
            dataset = "shemo_f"
        elif first == "M":
            dataset = "shemo_m"
        else:
            continue
        copied += copy_file(wav, clean_audio / dataset / wav.name)
    return copied


def ensure_shemo_extracted(source: Path) -> None:
    for name in ("female", "male"):
        target = source / name
        if any(target.glob("*.wav")):
            continue
        archive = source / f"{name}.zip"
        if not archive.exists():
            continue
        target.mkdir(parents=True, exist_ok=True)
        print(f"  extracting ShEMO {name}.zip")
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(target)


def counts(clean_audio: Path) -> dict[str, int]:
    return {dataset: len(list((clean_audio / dataset).glob("*.wav"))) for dataset in DATASETS}


def main() -> None:
    parser = argparse.ArgumentParser(description="Organize SER datasets for the upstream stress backbone.")
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--clean-audio", type=Path, required=True)
    args = parser.parse_args()

    resources = args.resources.resolve()
    clean_audio = args.clean_audio.resolve()
    ensure_dirs(clean_audio)

    copied = {
        "ravdess": organize_ravdess(resources, clean_audio),
        "cremad": organize_cremad(resources, clean_audio),
        "emodb": organize_emodb(resources, clean_audio),
        "shemo": organize_shemo(resources, clean_audio),
    }

    print("Copied/updated files:")
    for name, total in copied.items():
        print(f"  {name}: {total}")

    print("Clean audio counts:")
    for dataset, total in counts(clean_audio).items():
        print(f"  {dataset}: {total}")


if __name__ == "__main__":
    main()
