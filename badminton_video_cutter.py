# -*- coding: utf-8 -*-
# =============================================================================
# Badminton Video Cutter - 배드민턴 동영상 컷 프로그램 (단일 Python 소스)
# =============================================================================
# [프로그램 전체 기능 / 동작 / 로그 명세]
#  1. Windows Python 3.12 / PySide6 기반 데스크톱 GUI. 별도 Python 모듈 없음.
#  2. MP4/MOV/AVI/MKV/WEBM 등 로컬 동영상 불러오기, 화면/오디오 재생.
#  3. 재생·일시정지, 타임라인 탐색, 0.25~2배속, 현재 위치/전체 길이 표시.
#  4. FFprobe로 실제 동영상 메타데이터(길이/FPS/해상도)를 조회; FPS를
#     확인한 동영상은 추정 프레임 간격으로 전/후 이동(가변 FPS는 근사치).
#  5. 현재 시점 IN/OUT 표시, 구간 길이 검증, 여러 컷 추가·삭제·전체 삭제.
#  6. 컷별 스트로크 종류와 메모 기록, 표에서 종류/메모 직접 수정.
#  7. 컷 목록 선택→그 구간 시작으로 이동, 선택 컷 또는 IN/OUT 반복 재생.
#  8. 구간 위치를 표시하는 시각적 타임라인; 클릭으로 해당 시점 이동.
#  9. 편집 프로젝트(.bcut.json) 저장·불러오기; 원본 경로·구간·메모 보관.
# 10. FFmpeg를 통한 다중 컷 일괄 MP4 내보내기(QThread 백그라운드 작업).
# 11. 정밀 모드(H.264/AAC 재인코딩) 및 빠른 모드(원본 스트림 복사,
#     키프레임 위치에 따른 컷 오차 가능) 제공.
# 12. 내보내기 진행률 표시, 작업 취소 요청, 파일별 성공/실패 내역 표시.
# 13. 원본 절대 수정/삭제 금지. 임시 .part.mp4 파일 완성 후 파일명 변경.
# 14. 출력 이름 자동 안전화 및 기존 파일 덮어쓰기 방지(번호 자동 증가).
# 15. 성공한 컷을 clips_manifest_*.json / .csv에 저장(AI 데이터셋 연계).
# 16. 앱 실행/열기/프로젝트/수정/인코딩/오류/취소 로그를 UI와
#     logs/badminton_video_cutter.log(회전 로그)에 동시에 기록.
# 17. FFmpeg/FFprobe를 실행파일 주변 또는 PATH에서 탐색; 오류 안내.
# 18. 단축키: Ctrl+O(동영상), Ctrl+S(프로젝트 저장), Ctrl+Shift+S(다른
#     이름 저장), Ctrl+E(내보내기), Space(재생), I/O(IN/OUT),
#     N(컷 추가), Delete(선택 컷 삭제), 좌/우 방향키(프레임 근사 이동).
# 19. 작업 중 소스/프로젝트 변경 방지, 종료 전 변경 사항 확인.
# 20. 프로젝트와 로그는 별도 생성 데이터이며 소스 파일은 이 1개뿐.
# 21. FFprobe에서 원본 영상 코덱(AV1/H.264 등) 확인 및 UI/로그 표시.
# 22. AV1은 Qt 재생 오류를 피하도록 원본을 곧바로 열지 않고
#     FFmpeg로 H.264/AAC 호환 미리보기(proxy)를 자동 생성해 재생.
# 23. 비AV1 영상도 재생 오류 발생 시 "호환 미리보기 생성" 수동 전환 지원.
# 24. 40분 이상 긴 영상도 QThread에서 호환 미리보기 생성; 진행률·취소 지원.
# 25. RTX 그래픽카드를 위한 NVENC 인코딩 우선 시도, 실패하면 libx264
#     CPU 인코딩으로 자동 재시도(FFmpeg 빌드/드라이버 호환성 대비).
# 26. 미리보기 최대 1280px 가로/30fps로 변환해 디코딩/저장 부담 감소.
# 27. 원본 경로·파일 크기·수정시각 SHA256 캐시 키로 호환 미리보기 재사용.
# 28. 미리보기는 preview_cache/ 별도 저장, .gitignore로 Git에서 제외;
#     중간 실패·취소 시 .part.mp4 삭제, 원본 동영상은 절대 변경하지 않음.
# 29. IN/OUT, 구간 반복, JSON/CSV 메타데이터, 컷 내보내기는 항상
#     FFprobe로 읽은 원본 시간축과 원본 동영상을 기준으로 수행.
# 30. Qt 하드웨어 디코딩 환경 설정은 PySide6 import 이전에 적용.
# 31. 미리보기 생성 중 원본 변경·프로젝트 로드·내보내기·종료를 제한,
#     취소 후 스레드/임시파일을 정리. 기존 기능/단축키/로그를 유지.
#
# 필요 패키지: pip install PySide6
# 필요 외부 실행파일: ffmpeg, ffprobe (PATH 또는 이 파일과 같은 폴더)
# 실행: python badminton_video_cutter.py
# =============================================================================

from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime
from fractions import Fraction
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Optional

# Windows/Qt에서 AV1 하드웨어 디코더 초기화 오류 반복을 줄이기 위한 설정.
# AV1 재생은 아래 환경변수만 믿지 않고 H.264 미리보기 변환으로 우회한다.
os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", ",")

from PySide6.QtCore import QObject, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPen, QShortcut, QKeySequence
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QSlider, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QAbstractItemView,
)

APP_NAME = "Badminton Video Cutter"
APP_VERSION = "1.1.0"
SOURCE_EXTENSIONS = "동영상 (*.mp4 *.mov *.avi *.mkv *.webm *.m4v *.MP4 *.MOV *.AVI *.MKV);;모든 파일 (*)"
LABELS = ["포핸드 스매시", "오버헤드 클리어", "드롭", "드라이브", "헤어핀", "푸시", "리프트", "서브", "백핸드", "풋워크", "기타"]
MAX_EXPORT_SEGMENTS = 10000


def app_dir() -> Path:
    return Path(__file__).resolve().parent


def make_logger() -> logging.Logger:
    log = logging.getLogger("badminton_video_cutter")
    log.setLevel(logging.INFO)
    if not log.handlers:
        log_dir = app_dir() / "logs"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            fh = RotatingFileHandler(
                log_dir / "badminton_video_cutter.log",
                maxBytes=2_000_000, backupCount=3, encoding="utf-8",
            )
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            log.addHandler(fh)
        except OSError as exc:
            print(f"로그 파일 생성 실패: {exc}", file=sys.stderr)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        log.addHandler(sh)
    return log


LOGGER = make_logger()


def fmt_ms(ms: int) -> str:
    ms = max(0, int(ms))
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"


def fmt_seconds(ms: int) -> str:
    return f"{max(0, ms) / 1000:.3f}"


def sanitize_name(s: str) -> str:
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s)
    s = re.sub(r"\s+", "_", s).strip(" ._")
    if not s:
        s = "clip"
    # Windows reserved file names, including names followed by extensions
    if s.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        s = "_" + s
    return s[:90]


def find_tool(name: str) -> Optional[str]:
    exe = name + (".exe" if os.name == "nt" else "")
    local = app_dir() / exe
    if local.is_file():
        return str(local)
    return shutil.which(name)


def probe_video(path: Path) -> dict:
    tool = find_tool("ffprobe")
    if not tool:
        return {}
    cmd = [tool, "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=avg_frame_rate,width,height,codec_name:format=duration",
           "-of", "json", str(path)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=20,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if proc.returncode:
            LOGGER.warning("FFprobe 오류: %s", proc.stderr.strip())
            return {}
        data = json.loads(proc.stdout)
        stream = (data.get("streams") or [{}])[0]
        result = {
            "codec": str(stream.get("codec_name") or "unknown").lower(),
            "width": int(stream.get("width") or 0),
            "height": int(stream.get("height") or 0),
            "duration_ms": int(float(data.get("format", {}).get("duration") or 0) * 1000),
        }
        try:
            fps = float(Fraction(stream.get("avg_frame_rate") or "0"))
            result["fps"] = fps if 0 < fps < 1000 else None
        except (ValueError, ZeroDivisionError):
            result["fps"] = None
        return result
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
        LOGGER.warning("FFprobe 분석 실패: %s", exc)
        return {}


@dataclass
class Segment:
    number: int
    start_ms: int
    end_ms: int
    label: str
    note: str = ""


class SegmentTimeline(QWidget):
    seekRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration_ms = 0
        self.position_ms = 0
        self.in_ms: Optional[int] = None
        self.out_ms: Optional[int] = None
        self.segments: list[Segment] = []
        self.setMinimumHeight(32)
        self.setToolTip("색상 구간은 추가된 컷입니다. 클릭하면 해당 위치로 이동합니다.")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(9, 8, -9, -8)
        p.fillRect(rect, QColor("#dbe2eb"))
        if self.duration_ms <= 0 or rect.width() <= 0:
            return
        def x(ms: int) -> int:
            return rect.left() + round(rect.width() * max(0, min(ms, self.duration_ms)) / self.duration_ms)
        if self.in_ms is not None and self.out_ms is not None and self.out_ms > self.in_ms:
            p.fillRect(x(self.in_ms), rect.top(), max(1, x(self.out_ms)-x(self.in_ms)), rect.height(), QColor("#a4d7f8"))
        for seg in self.segments:
            p.fillRect(x(seg.start_ms), rect.top(), max(2, x(seg.end_ms)-x(seg.start_ms)), rect.height(), QColor("#33a184"))
        p.setPen(QPen(QColor("#e99a15"), 2))
        px = x(self.position_ms)
        p.drawLine(px, rect.top()-5, px, rect.bottom()+5)

    def mousePressEvent(self, event):
        if self.duration_ms and event.button() == Qt.MouseButton.LeftButton:
            width = max(1, self.width()-18)
            ratio = max(0.0, min(1.0, (event.position().x()-9)/width))
            self.seekRequested.emit(round(self.duration_ms * ratio))
        super().mousePressEvent(event)


class ExportWorker(QObject):
    progress = Signal(int, int, str)
    message = Signal(str)
    completed = Signal(list, int, bool, str)
    # completed: successes, failures, cancelled, manifest_path

    def __init__(self, ffmpeg: str, source: str, dest: str,
                 segments: list[Segment], mode: str, fps: Optional[float], cancel_event: threading.Event):
        super().__init__()
        self.ffmpeg = ffmpeg
        self.source = source
        self.dest = dest
        self.segments = [Segment(**asdict(s)) for s in segments]
        self.mode = mode
        self.fps = fps
        self.cancel_event = cancel_event

    def run(self):
        successes: list[dict] = []
        failure_count = 0
        manifest_file = ""
        reserved: set[Path] = set()
        try:
            folder = Path(self.dest)
            folder.mkdir(parents=True, exist_ok=True)
            for index, seg in enumerate(self.segments, start=1):
                if self.cancel_event.is_set():
                    break
                base = sanitize_name(f"{Path(self.source).stem}_{seg.number:03}_{seg.label}")
                final = folder / (base + ".mp4")
                suffix = 2
                while final.exists() or final in reserved:
                    final = folder / f"{base}_{suffix}.mp4"
                    suffix += 1
                reserved.add(final)
                tmp = final.with_name(final.stem + ".part.mp4")
                # 임시 파일도 중복·기존 파일 덮어쓰기를 피한다.
                k = 2
                while tmp.exists():
                    tmp = final.with_name(f"{final.stem}.part{k}.mp4")
                    k += 1
                duration = seg.end_ms - seg.start_ms
                self.message.emit(f"내보내기 {index}/{len(self.segments)}: {final.name}")
                cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                       "-ss", fmt_seconds(seg.start_ms), "-i", self.source,
                       "-t", fmt_seconds(duration), "-map", "0:v:0", "-map", "0:a?", "-sn", "-dn"]
                if self.mode == "accurate":
                    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                            "-movflags", "+faststart"]
                else:
                    cmd += ["-c", "copy", "-avoid_negative_ts", "make_zero"]
                cmd += ["-progress", "pipe:1", "-stats_period", "0.3", str(tmp)]
                error = ""
                proc = None
                try:
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True, encoding="utf-8", errors="replace",
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    assert proc.stdout is not None
                    last = 0
                    for line in proc.stdout:
                        if self.cancel_event.is_set():
                            proc.terminate()
                            break
                        line = line.strip()
                        if line.startswith("out_time_us="):
                            try:
                                encoded = int(line.split("=", 1)[1]) // 1000
                                last = max(last, min(duration, encoded))
                                overall = round(100 * ((index - 1) + last / max(1, duration)) / len(self.segments))
                                self.progress.emit(overall, index, final.name)
                            except ValueError:
                                pass
                    try:
                        proc.wait(timeout=5 if self.cancel_event.is_set() else 60)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    if proc.stderr:
                        error = proc.stderr.read().strip()
                    if self.cancel_event.is_set():
                        self.message.emit("사용자 취소: 진행 중 파일은 버립니다.")
                    elif proc.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
                        # 최종 파일명은 성공 시점에만 확정됩니다.
                        os.replace(tmp, final)
                        successes.append({
                            "source_video": self.source,
                            "clip_file": str(final),
                            "segment_number": seg.number,
                            "start_ms": seg.start_ms,
                            "end_ms": seg.end_ms,
                            "start_time": fmt_ms(seg.start_ms),
                            "end_time": fmt_ms(seg.end_ms),
                            "duration_ms": duration,
                            "label": seg.label,
                            "note": seg.note,
                            "fps_estimate": self.fps,
                            "export_mode": self.mode,
                        })
                        self.message.emit(f"성공: {final.name}")
                        self.progress.emit(round(index * 100 / len(self.segments)), index, final.name)
                    else:
                        failure_count += 1
                        self.message.emit(f"실패: {final.name} / {error or 'FFmpeg 출력 파일을 만들지 못했습니다.'}")
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    failure_count += 1
                    self.message.emit(f"실패: {final.name} / {exc}")
                finally:
                    if proc and proc.poll() is None:
                        proc.kill()
                        proc.wait()
                    try:
                        tmp.unlink(missing_ok=True)
                    except OSError as exc:
                        self.message.emit(f"임시 파일 삭제 실패: {tmp}: {exc}")
            if successes:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                json_path = folder / f"clips_manifest_{stamp}.json"
                csv_path = folder / f"clips_manifest_{stamp}.csv"
                payload = {"app": APP_NAME, "version": APP_VERSION,
                           "created_at": datetime.now().isoformat(timespec="seconds"),
                           "clips": successes}
                json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=list(successes[0].keys()))
                    writer.writeheader()
                    writer.writerows(successes)
                manifest_file = str(json_path)
                self.message.emit(f"JSON/CSV 메타데이터 저장: {json_path.name}, {csv_path.name}")
        except Exception as exc:
            failure_count += 1
            self.message.emit(f"내보내기 전체 오류: {type(exc).__name__}: {exc}")
            LOGGER.exception("내보내기 작업 오류")
        self.completed.emit(successes, failure_count, self.cancel_event.is_set(), manifest_file)


def proxy_target(source: Path) -> Path:
    """파일이 바뀌었을 때만 미리보기 캐시를 갱신하기 위한 고유 키."""
    info = source.stat()
    identity = f"{os.path.normcase(str(source.resolve()))}\n{info.st_size}\n{info.st_mtime_ns}\nproxy-v1-1280-30fps"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    return app_dir() / "preview_cache" / f"{sanitize_name(source.stem)[:40]}_{digest}.mp4"


class PreviewWorker(QObject):
    """GUI를 멈추지 않게 FFmpeg를 백그라운드에서 실행하는 미리보기 변환 작업."""
    progress = Signal(int, str)
    message = Signal(str)
    completed = Signal(str, bool, str)  # path, cancelled, error

    def __init__(self, ffmpeg: str, source: Path, dest: Path, duration_ms: int,
                 cancel_event: threading.Event):
        super().__init__()
        self.ffmpeg = ffmpeg
        self.source = source
        self.dest = dest
        self.duration_ms = duration_ms
        self.cancel_event = cancel_event

    def run(self):
        error = ""
        try:
            self.dest.parent.mkdir(parents=True, exist_ok=True)
            # 1차 GPU 인코딩(NVIDIA NVENC), 2차 CPU 인코딩(libx264).
            # 원본 AV1 디코딩은 FFmpeg 기본 소프트웨어 디코더를 사용한다.
            for codec_name, encode_opts in [
                ("NVENC GPU", ["-c:v", "h264_nvenc", "-preset", "fast", "-cq", "28", "-b:v", "0"]),
                ("libx264 CPU", ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "27"]),
            ]:
                if self.cancel_event.is_set():
                    break
                tmp = self.dest.with_name(self.dest.stem + f".{os.getpid()}.{int(time.time_ns())}.part.mp4")
                self.message.emit(f"미리보기 변환 시작: {codec_name} / {self.source.name}")
                # AV1의 GPU 가속 디코딩은 명시적으로 꺼서, RTX 20xx AV1 문제를 피한다.
                cmd = [self.ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
                       "-progress", "pipe:1", "-stats_period", "0.5", "-hwaccel", "none",
                       "-i", str(self.source), "-map", "0:v:0", "-map", "0:a:0?",
                       "-vf", "fps=30,scale=w='min(1280,iw)':h=-2",
                       *encode_opts, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
                       "-sn", "-dn", "-map_metadata", "-1", "-movflags", "+faststart", str(tmp)]
                proc = None
                try:
                    # stderr를 별도 임시 파일로 받으면 pipe 버퍼 정체가 발생하지 않는다.
                    import tempfile
                    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as err_file:
                        proc = subprocess.Popen(
                            cmd, stdout=subprocess.PIPE, stderr=err_file, text=True,
                            encoding="utf-8", errors="replace",
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                        assert proc.stdout is not None
                        for line in proc.stdout:
                            if self.cancel_event.is_set():
                                proc.terminate()
                                break
                            if line.startswith("out_time_us="):
                                try:
                                    encoded_ms = max(0, int(line.split("=", 1)[1]) // 1000)
                                    pct = min(99, int(encoded_ms * 100 / max(1, self.duration_ms)))
                                    self.progress.emit(pct, f"{codec_name} / {fmt_ms(encoded_ms)}")
                                except ValueError:
                                    pass
                        proc.stdout.close()
                        try:
                            proc.wait(timeout=8 if self.cancel_event.is_set() else 120)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait()
                        err_file.seek(0)
                        error = err_file.read().strip()[-1600:]
                    if not self.cancel_event.is_set() and proc.returncode == 0 and tmp.is_file() and tmp.stat().st_size > 0:
                        os.replace(tmp, self.dest)
                        self.progress.emit(100, "호환 미리보기 준비 완료")
                        self.message.emit(f"미리보기 생성 완료 ({codec_name}): {self.dest}")
                        self.completed.emit(str(self.dest), False, "")
                        return
                    if self.cancel_event.is_set():
                        self.message.emit("호환 미리보기 생성 취소")
                        break
                    self.message.emit(f"{codec_name} 변환 실패: {error or f'FFmpeg 반환코드 {proc.returncode}'}")
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    self.message.emit(f"{codec_name} 변환 실행 오류: {error}")
                finally:
                    if proc and proc.poll() is None:
                        proc.kill()
                        proc.wait()
                    try:
                        tmp.unlink(missing_ok=True)
                    except OSError as exc:
                        self.message.emit(f"미리보기 임시파일 정리 실패: {exc}")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self.message.emit(f"미리보기 생성 실패: {error}")
            LOGGER.exception("미리보기 변환 예외")
        self.completed.emit("", self.cancel_event.is_set(), error or "NVENC/CPU 인코딩 실패")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_path: Optional[Path] = None
        self.project_path: Optional[Path] = None
        self.duration_ms = 0
        self.fps: Optional[float] = None
        self.in_ms: Optional[int] = None
        self.out_ms: Optional[int] = None
        self.segments: list[Segment] = []
        self.next_number = 1
        self.dirty = False
        self.is_dragging = False
        self.is_reloading_table = False
        self.thread: Optional[QThread] = None
        self.worker: Optional[ExportWorker] = None
        self.cancel_event: Optional[threading.Event] = None
        self.export_active = False
        self.source_codec = "unknown"
        self.source_duration_ms = 0
        self.preview_path: Optional[Path] = None
        self.using_proxy = False
        self.preview_active = False
        self.preview_thread: Optional[QThread] = None
        self.preview_worker: Optional[PreviewWorker] = None
        self.preview_cancel_event: Optional[threading.Event] = None
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1350, 900)
        self.setMinimumSize(950, 650)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.7)
        self._build_ui()
        self._connect_media()
        self._make_actions()
        self._set_title()
        self._set_media_enabled(False)
        self.log(f"프로그램 시작: v{APP_VERSION}")
        self.log(f"FFmpeg 위치: {find_tool('ffmpeg') or '찾지 못함'}")
        self.log(f"FFprobe 위치: {find_tool('ffprobe') or '찾지 못함'}")
        self.log(f"Qt 디코딩 설정: QT_FFMPEG_DECODING_HW_DEVICE_TYPES={os.environ.get('QT_FFMPEG_DECODING_HW_DEVICE_TYPES')!r}")

    def _build_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(12, 12, 12, 10)
        main.setSpacing(8)
        head = QHBoxLayout()
        self.open_btn = QPushButton("동영상 열기 (Ctrl+O)")
        self.open_btn.clicked.connect(self.open_video)
        head.addWidget(self.open_btn)
        self.filename_label = QLabel("동영상 파일을 선택하세요")
        self.filename_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        head.addWidget(self.filename_label, 1)
        self.video_info = QLabel("FPS: -    해상도: -")
        head.addWidget(self.video_info)
        main.addLayout(head)

        pane = QSplitter(Qt.Orientation.Horizontal)
        main.addWidget(pane, 4)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 6, 0)
        self.video = QVideoWidget()
        self.video.setMinimumHeight(255)
        self.player.setVideoOutput(self.video)
        ll.addWidget(self.video, 1)
        controls = QHBoxLayout()
        self.play_btn = QPushButton("▶ 재생")
        self.play_btn.clicked.connect(self.toggle_play)
        controls.addWidget(self.play_btn)
        self.prev_btn = QPushButton("◀ 1프레임")
        self.prev_btn.clicked.connect(lambda: self.step_frame(-1))
        controls.addWidget(self.prev_btn)
        self.next_btn = QPushButton("1프레임 ▶")
        self.next_btn.clicked.connect(lambda: self.step_frame(1))
        controls.addWidget(self.next_btn)
        controls.addWidget(QLabel("배속"))
        self.speed = QComboBox()
        self.speed.addItems(["0.25x", "0.5x", "1.0x", "1.5x", "2.0x"])
        self.speed.setCurrentText("1.0x")
        self.speed.currentTextChanged.connect(lambda text: self.player.setPlaybackRate(float(text[:-1])))
        controls.addWidget(self.speed)
        self.time_label = QLabel("00:00:00.000 / 00:00:00.000")
        controls.addWidget(self.time_label, 1, Qt.AlignmentFlag.AlignRight)
        ll.addLayout(controls)
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setRange(0, 0)
        self.seek.sliderPressed.connect(self._seek_pressed)
        self.seek.sliderReleased.connect(self._seek_released)
        self.seek.sliderMoved.connect(self._seek_moved)
        ll.addWidget(self.seek)
        self.timeline = SegmentTimeline()
        self.timeline.seekRequested.connect(self.seek_to)
        ll.addWidget(self.timeline)
        pane.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(5, 0, 0, 0)
        mark_group = QGroupBox("컷 구간 설정")
        mg = QVBoxLayout(mark_group)
        row = QHBoxLayout()
        self.in_btn = QPushButton("IN 지정 (I)")
        self.in_btn.clicked.connect(self.mark_in)
        self.out_btn = QPushButton("OUT 지정 (O)")
        self.out_btn.clicked.connect(self.mark_out)
        row.addWidget(self.in_btn)
        row.addWidget(self.out_btn)
        mg.addLayout(row)
        self.range_label = QLabel("IN: 미설정     OUT: 미설정")
        mg.addWidget(self.range_label)
        self.loop_check = QCheckBox("선택 컷 / IN-OUT 구간 반복 재생")
        mg.addWidget(self.loop_check)
        form = QFormLayout()
        self.label_combo = QComboBox()
        self.label_combo.addItems(LABELS)
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("예: 오른쪽 후방 코트에서 스매시")
        form.addRow("종류", self.label_combo)
        form.addRow("메모", self.note_edit)
        mg.addLayout(form)
        row2 = QHBoxLayout()
        self.add_btn = QPushButton("+ 컷 추가 (N)")
        self.add_btn.clicked.connect(self.add_segment)
        self.delete_btn = QPushButton("선택 컷 삭제 (Del)")
        self.delete_btn.clicked.connect(self.delete_selected)
        row2.addWidget(self.add_btn)
        row2.addWidget(self.delete_btn)
        mg.addLayout(row2)
        rl.addWidget(mark_group)

        preview_group = QGroupBox("영상 재생 호환성 (AV1 지원)")
        pg = QVBoxLayout(preview_group)
        self.preview_status = QLabel("영상 열기 후 코덱을 확인합니다.")
        self.preview_status.setWordWrap(True)
        pg.addWidget(self.preview_status)
        preview_row = QHBoxLayout()
        self.preview_btn = QPushButton("호환 미리보기 생성 / 사용")
        self.preview_btn.clicked.connect(self.start_preview_conversion)
        self.preview_btn.setEnabled(False)
        self.preview_cancel_btn = QPushButton("변환 취소")
        self.preview_cancel_btn.clicked.connect(self.cancel_preview_conversion)
        self.preview_cancel_btn.setEnabled(False)
        preview_row.addWidget(self.preview_btn, 1)
        preview_row.addWidget(self.preview_cancel_btn)
        pg.addLayout(preview_row)
        self.preview_progress = QProgressBar()
        self.preview_progress.setRange(0, 100)
        self.preview_progress.setValue(0)
        pg.addWidget(self.preview_progress)
        rl.addWidget(preview_group)

        out_group = QGroupBox("내보내기")
        og = QVBoxLayout(out_group)
        output_line = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("내보내기 폴더")
        self.folder_btn = QPushButton("찾기...")
        self.folder_btn.clicked.connect(self.choose_output_folder)
        output_line.addWidget(self.output_edit, 1)
        output_line.addWidget(self.folder_btn)
        og.addLayout(output_line)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("정밀 컷: 재인코딩 (권장)", "accurate")
        self.mode_combo.addItem("빠른 컷: 재인코딩 없음 (경계 오차 가능)", "copy")
        og.addWidget(self.mode_combo)
        export_buttons = QHBoxLayout()
        self.export_btn = QPushButton("모든 컷 MP4 저장 (Ctrl+E)")
        self.export_btn.clicked.connect(self.export_clips)
        self.cancel_btn = QPushButton("작업 취소")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_export)
        export_buttons.addWidget(self.export_btn, 1)
        export_buttons.addWidget(self.cancel_btn)
        og.addLayout(export_buttons)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        og.addWidget(self.progress)
        rl.addWidget(out_group)
        rl.addStretch(1)
        pane.addWidget(right)
        pane.setSizes([880, 440])

        self.cut_table = QTableWidget(0, 6)
        self.cut_table.setHorizontalHeaderLabels(["번호", "스트로크 종류", "시작", "종료", "길이", "메모 (편집 가능)"])
        self.cut_table.verticalHeader().setVisible(False)
        self.cut_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cut_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.cut_table.setAlternatingRowColors(True)
        self.cut_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for index in (2, 3, 4):
            self.cut_table.horizontalHeader().setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)
        self.cut_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.cut_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.cut_table.itemSelectionChanged.connect(self.on_segment_selected)
        self.cut_table.itemChanged.connect(self.on_table_item_changed)
        self.cut_table.setMinimumHeight(150)
        main.addWidget(QLabel("컷 목록 (종류·메모는 셀 더블클릭으로 수정)"))
        main.addWidget(self.cut_table, 2)
        footer = QHBoxLayout()
        self.count_label = QLabel("등록된 컷: 0개")
        footer.addWidget(self.count_label)
        footer.addStretch()
        self.clear_btn = QPushButton("컷 전체 삭제")
        self.clear_btn.clicked.connect(self.clear_segments)
        footer.addWidget(self.clear_btn)
        self.project_btn = QPushButton("프로젝트 저장 (Ctrl+S)")
        self.project_btn.clicked.connect(self.save_project)
        footer.addWidget(self.project_btn)
        main.addLayout(footer)
        main.addWidget(QLabel("작업 로그"))
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(1500)
        self.log_box.setMinimumHeight(90)
        main.addWidget(self.log_box, 1)
        self.statusBar().showMessage("준비됨")

    def _make_actions(self):
        menu = self.menuBar().addMenu("파일(&F)")
        items = [
            ("동영상 열기", "Ctrl+O", self.open_video),
            ("프로젝트 열기", "Ctrl+Shift+O", self.load_project),
            ("프로젝트 저장", "Ctrl+S", self.save_project),
            ("프로젝트 다른 이름으로 저장", "Ctrl+Shift+S", self.save_project_as),
            ("컷 내보내기", "Ctrl+E", self.export_clips),
        ]
        for text, shortcut, callback in items:
            action = QAction(text, self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            menu.addAction(action)
        menu.addSeparator()
        quit_action = QAction("종료", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)
        # 편집 가능한 텍스트/테이블에서 입력 중에는 문자 단축키를 빼앗지 않는다.
        for key, callback in [("Space", self.toggle_play), ("I", self.mark_in),
                              ("O", self.mark_out), ("N", self.add_segment),
                              ("Left", lambda: self.step_frame(-1)),
                              ("Right", lambda: self.step_frame(1))]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda cb=callback: self._shortcut_if_not_editing(cb))
        shortcut = QShortcut(QKeySequence("Delete"), self.cut_table)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(self.delete_selected)

    def _shortcut_if_not_editing(self, callback):
        from PySide6.QtWidgets import QLineEdit, QAbstractSpinBox, QPlainTextEdit, QTextEdit
        if isinstance(QApplication.focusWidget(), (QLineEdit, QAbstractSpinBox, QPlainTextEdit, QTextEdit)):
            return
        callback()

    def _connect_media(self):
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_play_state)
        self.player.errorOccurred.connect(self._on_media_error)

    def log(self, message: str, level: str = "info"):
        getattr(LOGGER, level, LOGGER.info)(message)
        self.log_box.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        self.statusBar().showMessage(message, 8000)

    def _set_title(self):
        file = self.project_path.name if self.project_path else (self.video_path.name if self.video_path else "새 프로젝트")
        self.setWindowTitle(f"{'*' if self.dirty else ''}{file} - {APP_NAME} v{APP_VERSION}")

    def _mark_dirty(self):
        self.dirty = True
        self._set_title()

    def _set_media_enabled(self, enabled: bool):
        for widget in (self.play_btn, self.in_btn, self.out_btn, self.add_btn, self.seek, self.speed):
            widget.setEnabled(enabled)
        self.prev_btn.setEnabled(enabled and self.fps is not None)
        self.next_btn.setEnabled(enabled and self.fps is not None)
        self._update_segment_controls()

    def _update_segment_controls(self):
        busy = self.export_active or self.preview_active
        self.delete_btn.setEnabled(bool(self.segments) and not busy)
        self.clear_btn.setEnabled(bool(self.segments) and not busy)
        self.export_btn.setEnabled(bool(self.segments) and not busy)
        self.project_btn.setEnabled(not busy)

    def _guard_export(self) -> bool:
        if self.export_active:
            QMessageBox.warning(self, "작업 중", "내보내기가 진행 중입니다. 완료 또는 취소 후 진행하세요.")
            return False
        if self.preview_active:
            QMessageBox.warning(self, "미리보기 생성 중", "호환 미리보기 생성이 진행 중입니다. 완료 또는 취소 후 진행하세요.")
            return False
        return True

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        reply = QMessageBox.question(self, "변경 내용 확인",
                                     "저장하지 않은 컷/프로젝트 변경 사항이 있습니다. 계속하면 사라집니다.\n계속할까요?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes

    def open_video(self):
        if not self._guard_export() or not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "배드민턴 영상 선택", str(Path.home()), SOURCE_EXTENSIONS)
        if path:
            self._load_video(Path(path), reset=True)

    def _load_video(self, path: Path, reset: bool):
        if not path.is_file():
            QMessageBox.critical(self, "파일 없음", f"동영상 파일을 찾을 수 없습니다.\n{path}")
            return False
        self.player.stop()
        self.player.setSource(QUrl())
        self.using_proxy = False
        self.preview_path = None
        self.video_path = path.resolve()
        if reset:
            self.segments = []
            self.next_number = 1
            self.in_ms = None
            self.out_ms = None
            self.project_path = None
            self.dirty = False
        info = probe_video(self.video_path)
        self.fps = info.get("fps")
        self.source_codec = info.get("codec", "unknown")
        self.duration_ms = info.get("duration_ms", 0)
        self.source_duration_ms = self.duration_ms
        self.video_info.setText(
            f"FPS: {self.fps:.3f}" if self.fps else "FPS: 확인 불가"
        )
        width, height = info.get("width", 0), info.get("height", 0)
        if width and height:
            self.video_info.setText(self.video_info.text() + f"    해상도: {width}×{height}")
        self.video_info.setText(self.video_info.text() + f"    코덱: {self.source_codec.upper()}")
        self.filename_label.setText(self.video_path.name)
        self.filename_label.setToolTip(str(self.video_path))
        self.output_edit.setText(str(self.video_path.parent / (self.video_path.stem + "_clips")))
        self.preview_status.setText(f"원본 코덱: {self.source_codec.upper()} / 재생 방식 확인 중")
        self.preview_progress.setValue(0)
        self.preview_btn.setEnabled(bool(find_tool("ffmpeg")))
        self.seek.setMaximum(self.duration_ms)
        self.seek.setValue(0)
        self.time_label.setText(f"{fmt_ms(0)} / {fmt_ms(self.duration_ms)}")
        self.timeline.position_ms = 0
        self.timeline.duration_ms = self.duration_ms
        self.timeline.in_ms = self.in_ms
        self.timeline.out_ms = self.out_ms
        self.timeline.segments = self.segments
        self.timeline.update()
        self._refresh_table()
        self._update_range_label()
        self._set_media_enabled(self.source_codec != "av1")
        self._set_title()
        self.log(f"동영상 열기: {self.video_path} / FPS={self.fps} / 길이={fmt_ms(self.duration_ms)} / 코덱={self.source_codec}")
        if self.source_codec == "av1":
            # AV1 원본을 Qt에 넘기지 않아 GPU 디코딩 에러 무한 반복을 방지한다.
            self.log("AV1 원본 탐지: Qt 직접 재생 대신 H.264 호환 미리보기를 생성합니다.")
            self.start_preview_conversion()
        else:
            self.player.setSource(QUrl.fromLocalFile(str(self.video_path)))
            self.preview_status.setText(f"원본 영상 직접 재생 / {self.source_codec.upper()} (검은 화면이면 호환 미리보기를 클릭)")
        if not find_tool("ffprobe"):
            self.log("FFprobe 미설치: FPS를 알 수 없으므로 프레임 이동이 비활성화됩니다.", "warning")
        return True

    def on_duration_changed(self, duration: int):
        # 미리보기 인코딩 프레임레이트 차이가 원본의 컷 구간 시간축을 바꾸지 않도록 한다.
        if duration > 0 and not (self.using_proxy and self.source_duration_ms > 0):
            self.duration_ms = duration
            self.seek.setMaximum(duration)
            self.timeline.duration_ms = duration
            self.timeline.update()
            self.time_label.setText(f"{fmt_ms(self.player.position())} / {fmt_ms(duration)}")

    def on_position_changed(self, pos: int):
        if not self.is_dragging:
            self.seek.setValue(pos)
        self.time_label.setText(f"{fmt_ms(pos)} / {fmt_ms(self.duration_ms)}")
        self.timeline.position_ms = pos
        self.timeline.update()
        if self.loop_check.isChecked() and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            bounds = self._loop_bounds()
            if bounds and pos >= bounds[1] and bounds[1] > bounds[0]:
                self.player.setPosition(bounds[0])

    def _loop_bounds(self) -> Optional[tuple[int, int]]:
        row = self.cut_table.currentRow()
        if 0 <= row < len(self.segments):
            seg = self.segments[row]
            return (seg.start_ms, seg.end_ms)
        if self.in_ms is not None and self.out_ms is not None and self.out_ms > self.in_ms:
            return (self.in_ms, self.out_ms)
        return None

    def _on_play_state(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_btn.setText("❚❚ 일시정지" if playing else "▶ 재생")
        if not playing and self.loop_check.isChecked() and self._loop_bounds():
            bounds = self._loop_bounds()
            if bounds and self.player.position() >= bounds[1] and self.duration_ms and self.player.position() >= self.duration_ms - 100:
                QTimer.singleShot(0, lambda: self._restart_loop_if_enabled(bounds[0]))

    def _restart_loop_if_enabled(self, start):
        if self.loop_check.isChecked() and self.video_path and not self.export_active:
            self.player.setPosition(start)
            self.player.play()

    def _on_media_error(self, error, error_string):
        if error != QMediaPlayer.Error.NoError:
            self.log(f"동영상 재생 오류: {error_string}", "error")
            if self.video_path and not self.using_proxy and not self.preview_active:
                self.preview_status.setText("직접 재생에 실패했습니다. '호환 미리보기 생성 / 사용'을 누르세요.")
                self.preview_btn.setEnabled(bool(find_tool("ffmpeg")))

    def start_preview_conversion(self):
        if not self.video_path or self.preview_active or self.export_active:
            return
        ffmpeg = find_tool("ffmpeg")
        if not ffmpeg:
            self.log("호환 미리보기 생성 실패: FFmpeg 설치가 필요합니다.", "error")
            QMessageBox.warning(self, "FFmpeg 필요", "호환 미리보기를 생성하려면 FFmpeg가 필요합니다.")
            return
        try:
            target = proxy_target(self.video_path)
        except OSError as exc:
            self.log(f"미리보기 캐시 경로 확인 실패: {exc}", "error")
            return
        if target.is_file() and target.stat().st_size > 1024:
            self.log(f"기존 호환 미리보기 재사용: {target}")
            self._use_preview_file(target)
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        self.player.setSource(QUrl())
        self._set_media_enabled(False)
        self.preview_active = True
        self.preview_cancel_event = threading.Event()
        self.preview_thread = QThread(self)
        self.preview_worker = PreviewWorker(ffmpeg, self.video_path, target,
                                            self.source_duration_ms, self.preview_cancel_event)
        self.preview_worker.moveToThread(self.preview_thread)
        self.preview_thread.started.connect(self.preview_worker.run)
        self.preview_worker.progress.connect(self._on_preview_progress)
        self.preview_worker.message.connect(self.log)
        self.preview_worker.completed.connect(self._on_preview_completed)
        self.preview_worker.completed.connect(self.preview_thread.quit)
        self.preview_thread.finished.connect(self.preview_worker.deleteLater)
        self.preview_thread.finished.connect(self.preview_thread.deleteLater)
        self.preview_thread.finished.connect(self._preview_thread_finished)
        self.preview_btn.setEnabled(False)
        self.preview_cancel_btn.setEnabled(True)
        self.preview_progress.setValue(0)
        self.preview_status.setText("H.264 호환 미리보기 생성 중… 원본은 변경되지 않습니다.")
        for widget in (self.open_btn, self.folder_btn, self.mode_combo, self.output_edit, self.cut_table):
            widget.setEnabled(False)
        self._update_segment_controls()
        self.log(f"미리보기 생성 요청: {self.video_path} -> {target}")
        self.preview_thread.start()

    def _on_preview_progress(self, pct: int, description: str):
        self.preview_progress.setValue(max(0, min(100, pct)))
        self.preview_status.setText(f"호환 미리보기 생성 중 {pct}% — {description}")

    def cancel_preview_conversion(self):
        if self.preview_active and self.preview_cancel_event:
            self.preview_cancel_event.set()
            self.preview_cancel_btn.setEnabled(False)
            self.log("호환 미리보기 생성 취소 요청", "warning")

    def _on_preview_completed(self, path: str, cancelled: bool, error: str):
        if path and not cancelled:
            self._use_preview_file(Path(path))
        else:
            self.preview_status.setText("미리보기 생성 취소됨" if cancelled else "미리보기 생성 실패 (로그를 확인하세요)")
            self.log("호환 미리보기 생성 취소" if cancelled else f"호환 미리보기 생성 실패: {error}",
                     "warning" if cancelled else "error")
            if not cancelled:
                QMessageBox.warning(self, "호환 미리보기 생성 실패", "FFmpeg 변환이 실패했습니다. 작업 로그를 확인하세요.\n" + error[-600:])
            # AV1인 경우 원본 Qt 재생 시도는 오류 반복이므로 중지한 채로 둔다.
            if self.source_codec != "av1":
                self.player.setSource(QUrl.fromLocalFile(str(self.video_path)))
                self._set_media_enabled(True)

    def _use_preview_file(self, path: Path):
        self.preview_path = path
        self.using_proxy = True
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.preview_progress.setValue(100)
        self.preview_status.setText("H.264 호환 미리보기로 재생 중 (내보내기는 원본 사용)")
        self._set_media_enabled(True)
        self.log(f"재생 소스 전환: 호환 미리보기={path} / 컷 내보내기 원본={self.video_path}")

    def _preview_thread_finished(self):
        self.preview_active = False
        self.preview_thread = None
        self.preview_worker = None
        self.preview_cancel_event = None
        self.preview_cancel_btn.setEnabled(False)
        self.preview_btn.setEnabled(bool(self.video_path and find_tool("ffmpeg")))
        for widget in (self.open_btn, self.folder_btn, self.mode_combo, self.output_edit, self.cut_table):
            widget.setEnabled(True)
        self._update_segment_controls()

    def _seek_pressed(self):
        self.is_dragging = True

    def _seek_moved(self, value: int):
        self.time_label.setText(f"{fmt_ms(value)} / {fmt_ms(self.duration_ms)}")
        self.timeline.position_ms = value
        self.timeline.update()

    def _seek_released(self):
        self.is_dragging = False
        self.seek_to(self.seek.value())

    def seek_to(self, pos: int):
        if self.video_path:
            self.player.setPosition(max(0, min(int(pos), self.duration_ms)))

    def toggle_play(self):
        if not self.video_path:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.loop_check.isChecked():
                bounds = self._loop_bounds()
                if bounds and not (bounds[0] <= self.player.position() < bounds[1]):
                    self.player.setPosition(bounds[0])
            self.player.play()

    def step_frame(self, delta: int):
        if not self.video_path or not self.fps:
            return
        self.player.pause()
        # 고정 FPS 기준 근사; Qt의 시간 기반 탐색이므로 VFR/코덱의 프레임 정밀 보장은 하지 않는다.
        self.seek_to(self.player.position() + round(delta * 1000 / self.fps))

    def mark_in(self):
        if not self.video_path:
            return
        self.in_ms = self.player.position()
        self.timeline.in_ms = self.in_ms
        self._update_range_label()
        self.timeline.update()
        self.log(f"IN 지정: {fmt_ms(self.in_ms)}")

    def mark_out(self):
        if not self.video_path:
            return
        self.out_ms = self.player.position()
        self.timeline.out_ms = self.out_ms
        self._update_range_label()
        self.timeline.update()
        self.log(f"OUT 지정: {fmt_ms(self.out_ms)}")

    def _update_range_label(self):
        a = fmt_ms(self.in_ms) if self.in_ms is not None else "미설정"
        b = fmt_ms(self.out_ms) if self.out_ms is not None else "미설정"
        self.range_label.setText(f"IN: {a}    OUT: {b}")

    def add_segment(self):
        if not self.video_path or self.export_active:
            return
        if self.in_ms is None or self.out_ms is None:
            QMessageBox.warning(self, "컷 구간 설정", "IN과 OUT을 먼저 지정하세요.")
            return
        if self.in_ms >= self.out_ms:
            QMessageBox.warning(self, "구간 오류", "OUT은 IN보다 뒤여야 합니다.")
            return
        if self.duration_ms and self.out_ms > self.duration_ms:
            QMessageBox.warning(self, "구간 오류", "OUT이 영상 길이를 초과합니다.")
            return
        if len(self.segments) >= MAX_EXPORT_SEGMENTS:
            QMessageBox.warning(self, "개수 제한", "컷은 최대 10,000개까지 등록할 수 있습니다.")
            return
        seg = Segment(self.next_number, self.in_ms, self.out_ms,
                      self.label_combo.currentText(), self.note_edit.text().strip())
        self.next_number += 1
        self.segments.append(seg)
        self._mark_dirty()
        self._refresh_table()
        self.cut_table.selectRow(len(self.segments) - 1)
        self.log(f"컷 추가 #{seg.number}: {seg.label} {fmt_ms(seg.start_ms)} ~ {fmt_ms(seg.end_ms)}")

    def _refresh_table(self):
        self.is_reloading_table = True
        self.cut_table.blockSignals(True)
        self.cut_table.setRowCount(len(self.segments))
        for row, seg in enumerate(self.segments):
            cells = [str(seg.number), seg.label, fmt_ms(seg.start_ms), fmt_ms(seg.end_ms),
                     fmt_ms(seg.end_ms - seg.start_ms), seg.note]
            for col, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if col not in (1, 5):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.cut_table.setItem(row, col, item)
        self.cut_table.blockSignals(False)
        self.is_reloading_table = False
        self.timeline.segments = self.segments
        self.timeline.update()
        self.count_label.setText(f"등록된 컷: {len(self.segments)}개")
        self._update_segment_controls()

    def on_table_item_changed(self, item):
        if self.is_reloading_table or self.export_active or self.preview_active:
            return
        row = item.row()
        if not 0 <= row < len(self.segments):
            return
        seg = self.segments[row]
        if item.column() == 1:
            seg.label = item.text().strip() or "기타"
        elif item.column() == 5:
            seg.note = item.text().strip()
        else:
            return
        self._mark_dirty()
        self.log(f"컷 수정 #{seg.number}: {seg.label}, 메모={seg.note}")

    def on_segment_selected(self):
        row = self.cut_table.currentRow()
        if 0 <= row < len(self.segments):
            seg = self.segments[row]
            self.player.pause()
            self.seek_to(seg.start_ms)
            self.statusBar().showMessage(f"컷 #{seg.number} 선택: {seg.label}", 5000)

    def delete_selected(self):
        if self.export_active or self.preview_active:
            return
        row = self.cut_table.currentRow()
        if not 0 <= row < len(self.segments):
            return
        seg = self.segments.pop(row)
        self._mark_dirty()
        self._refresh_table()
        self.log(f"컷 삭제 #{seg.number}: {seg.label}")

    def clear_segments(self):
        if not self.segments or self.export_active or self.preview_active:
            return
        if QMessageBox.question(self, "전체 삭제", "등록한 모든 컷을 삭제할까요?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        amount = len(self.segments)
        self.segments.clear()
        self._refresh_table()
        self._mark_dirty()
        self.log(f"컷 전체 삭제: {amount}개")

    def choose_output_folder(self):
        if self.export_active:
            return
        folder = QFileDialog.getExistingDirectory(self, "출력 폴더 선택", self.output_edit.text() or str(Path.home()))
        if folder:
            self.output_edit.setText(folder)
            self.log(f"출력 폴더 변경: {folder}")

    def save_project(self):
        if not self._guard_export():
            return False
        if not self.video_path:
            QMessageBox.warning(self, "저장할 동영상 없음", "먼저 동영상을 불러오세요.")
            return False
        if not self.project_path:
            return self.save_project_as()
        return self._write_project(self.project_path)

    def save_project_as(self):
        if not self._guard_export() or not self.video_path:
            return False
        default = str(self.project_path or self.video_path.with_suffix(".bcut.json"))
        path, _ = QFileDialog.getSaveFileName(self, "프로젝트 저장", default,
                                               "Badminton Cutter Project (*.bcut.json);;JSON (*.json)")
        if not path:
            return False
        if not path.lower().endswith(".json"):
            path += ".bcut.json"
        return self._write_project(Path(path))

    def _write_project(self, path: Path):
        # Windows에서 원본/프로젝트가 서로 다른 드라이브면 relpath가 ValueError를 낸다.
        try:
            relative_video_path = os.path.relpath(self.video_path, path.parent)
        except ValueError:
            relative_video_path = None
        data = {
            "format": "badminton-video-cutter-project", "version": 1,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "video_path": str(self.video_path),
            "video_relative_path": relative_video_path,
            "in_ms": self.in_ms, "out_ms": self.out_ms,
            "output_dir": self.output_edit.text(),
            "export_mode": self.mode_combo.currentData(),
            "segments": [asdict(s) for s in self.segments],
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # 임시 파일을 쓰고 교체하여 실패 시 기존 프로젝트 파일을 보존한다.
            temporary = path.with_name(path.name + ".tmp")
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, path)
        except OSError as exc:
            self.log(f"프로젝트 저장 실패: {exc}", "error")
            QMessageBox.critical(self, "프로젝트 저장 실패", str(exc))
            return False
        self.project_path = path
        self.dirty = False
        self._set_title()
        self.log(f"프로젝트 저장: {path} / 컷 {len(self.segments)}개")
        return True

    def load_project(self):
        if not self._guard_export() or not self._confirm_discard():
            return
        filename, _ = QFileDialog.getOpenFileName(self, "프로젝트 불러오기", str(app_dir()), "JSON 프로젝트 (*.bcut.json *.json)")
        if not filename:
            return
        path = Path(filename)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("format") != "badminton-video-cutter-project" or data.get("version") != 1:
                raise ValueError("지원하지 않는 프로젝트 형식/버전입니다.")
            video = Path(data["video_path"])
            if not video.is_file() and data.get("video_relative_path"):
                video = (path.parent / data["video_relative_path"]).resolve()
            if not video.is_file():
                raise FileNotFoundError(f"원본 동영상을 찾을 수 없습니다: {data['video_path']}")
            segments = []
            for item in data.get("segments", []):
                seg = Segment(number=int(item["number"]), start_ms=int(item["start_ms"]),
                              end_ms=int(item["end_ms"]), label=str(item["label"]),
                              note=str(item.get("note", "")))
                if seg.start_ms < 0 or seg.end_ms <= seg.start_ms:
                    raise ValueError(f"컷 #{seg.number}의 시작/종료 값이 올바르지 않습니다.")
                segments.append(seg)
            if len(segments) > MAX_EXPORT_SEGMENTS:
                raise ValueError("컷 최대 개수(10,000개)를 초과했습니다.")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            QMessageBox.critical(self, "프로젝트 읽기 실패", str(exc))
            self.log(f"프로젝트 열기 실패: {path}: {exc}", "error")
            return
        if not self._load_video(video, reset=True):
            return
        self.segments = segments
        self.next_number = max((s.number for s in segments), default=0) + 1
        self.in_ms = int(data["in_ms"]) if data.get("in_ms") is not None else None
        self.out_ms = int(data["out_ms"]) if data.get("out_ms") is not None else None
        self.timeline.in_ms = self.in_ms
        self.timeline.out_ms = self.out_ms
        self.output_edit.setText(str(data.get("output_dir") or self.output_edit.text()))
        mode = self.mode_combo.findData(data.get("export_mode", "accurate"))
        self.mode_combo.setCurrentIndex(max(0, mode))
        self.project_path = path
        self.dirty = False
        self._refresh_table()
        self._update_range_label()
        self._set_title()
        self.log(f"프로젝트 불러오기: {path} / 컷 {len(segments)}개")

    def export_clips(self):
        if self.export_active or self.preview_active or not self.video_path or not self.segments:
            return
        ffmpeg = find_tool("ffmpeg")
        if not ffmpeg:
            QMessageBox.critical(self, "FFmpeg 필요",
                                 "FFmpeg 실행 파일을 찾을 수 없습니다.\n"
                                 "README의 FFmpeg 설치/환경변수 안내를 따라 설치하거나\n"
                                 "ffmpeg.exe를 소스 파일과 같은 폴더에 넣으세요.")
            self.log("내보내기 실패: FFmpeg 실행 파일 없음", "error")
            return
        folder_text = self.output_edit.text().strip()
        if not folder_text:
            QMessageBox.warning(self, "출력 폴더", "출력 폴더를 지정하세요.")
            return
        output = Path(folder_text).expanduser()
        if output.resolve() == self.video_path.resolve():
            QMessageBox.warning(self, "출력 폴더 오류", "출력 폴더를 지정해야 합니다.")
            return
        for seg in self.segments:
            if seg.start_ms < 0 or seg.end_ms <= seg.start_ms:
                QMessageBox.warning(self, "컷 구간 오류", f"컷 #{seg.number}의 구간이 올바르지 않습니다.")
                return
            if self.duration_ms and seg.end_ms > self.duration_ms + 250:
                QMessageBox.warning(self, "컷 구간 오류", f"컷 #{seg.number}의 끝이 영상 길이보다 깁니다.")
                return
        self.cancel_event = threading.Event()
        self.thread = QThread(self)
        self.worker = ExportWorker(ffmpeg, str(self.video_path), str(output.resolve()),
                                   self.segments, self.mode_combo.currentData(), self.fps,
                                   self.cancel_event)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_export_progress)
        self.worker.message.connect(self.log)
        self.worker.completed.connect(self._on_export_completed)
        self.worker.completed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._export_thread_finished)
        self.export_active = True
        self.progress.setValue(0)
        self.cancel_btn.setEnabled(True)
        for widget in (self.open_btn, self.folder_btn, self.mode_combo, self.output_edit,
                       self.in_btn, self.out_btn, self.add_btn, self.cut_table):
            widget.setEnabled(False)
        self._update_segment_controls()
        self.log(f"내보내기 시작: {len(self.segments)}개 / 모드={self.mode_combo.currentData()} / 대상={output}")
        self.thread.start()

    def _on_export_progress(self, pct: int, index: int, name: str):
        self.progress.setValue(max(0, min(100, pct)))
        self.statusBar().showMessage(f"내보내기 {index}/{len(self.segments)}: {name} - {pct}%")

    def cancel_export(self):
        if self.export_active and self.cancel_event:
            self.cancel_event.set()
            self.cancel_btn.setEnabled(False)
            self.log("취소 요청: 현재 FFmpeg 작업 종료 후 정리합니다.", "warning")

    def _on_export_completed(self, successes: list, failures: int, cancelled: bool, manifest_path: str):
        self.progress.setValue(100 if not cancelled and failures == 0 else self.progress.value())
        summary = f"내보내기 종료: 성공 {len(successes)}개 / 실패 {failures}개 / 취소 {'예' if cancelled else '아니오'}"
        self.log(summary, "warning" if cancelled or failures else "info")
        if manifest_path:
            self.log(f"메타데이터 위치: {manifest_path}")
        QMessageBox.information(self, "내보내기 결과", summary + (f"\nJSON: {manifest_path}" if manifest_path else ""))

    def _export_thread_finished(self):
        self.export_active = False
        self.worker = None
        self.thread = None
        self.cancel_event = None
        self.cancel_btn.setEnabled(False)
        for widget in (self.open_btn, self.folder_btn, self.mode_combo, self.output_edit,
                       self.in_btn, self.out_btn, self.add_btn, self.cut_table):
            widget.setEnabled(True)
        self._update_segment_controls()

    def closeEvent(self, event):
        if self.preview_active:
            QMessageBox.warning(self, "미리보기 생성 중", "호환 미리보기 작업을 취소하거나 완료한 뒤 종료하세요.")
            event.ignore()
            return
        if self.export_active:
            QMessageBox.warning(self, "내보내기 진행 중", "작업 취소 또는 완료 후 종료하세요.")
            event.ignore()
            return
        if not self._confirm_discard():
            event.ignore()
            return
        self.log("프로그램 종료")
        self.player.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("맑은 고딕" if os.name == "nt" else "Sans Serif", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
