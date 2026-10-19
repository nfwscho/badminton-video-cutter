# Badminton Video Cutter v1.2.0

배드민턴 경기/레슨 원본 동영상에서 여러 스트로크 구간을 잘라 **각각 MP4로 일괄 저장**하고, 이후 AI 자세 분석/데이터셋 정리에 활용할 수 있도록 **JSON·CSV 메타데이터**를 만드는 Windows 데스크톱 프로그램입니다.

- **실행 소스는 `badminton_video_cutter.py` 단 한 개**입니다. 별도 Python 패키지 구조나 Docker를 사용하지 않습니다.
- 다른 파일은 사용 설명서(`README.md`), 설치 및 Git 순서별 안내서(`INSTALL.md`), Git 제외 규칙(`.gitignore`)입니다.
- 실행 중 `logs/`, `preview_cache/`, 영상 출력 폴더, `.bcut.json` 프로젝트 파일 등이 생길 수 있습니다.
- **v1.2 개선 (권장)**: VLC 64비트 + `python-vlc`를 설치하면 **AV1 영상을 원본 상태로 즉시 재생**합니다. 40분 영상을 20분 동안 사전 변환할 필요가 없습니다.  기존 FFmpeg 호환 미리보기(H.264)는 문제가 생길 때의 예비 기능으로 보존합니다.
- **v1.1 유지**: 필요 시 미리보기를 백그라운드에서 변환하고, NVIDIA NVENC가 실패하면 CPU로 자동 재시도합니다. 원본 컷 내보내기와 JSON/CSV 등은 기존과 동일합니다.

## 1. 준비 환경

- **Windows 10/11**, **Python 3.12**, PowerShell
- **PySide6**: 프로그램 GUI (VLC가 없으면 Qt 기본 재생 사용)
- **VLC 64비트 + python-vlc**: AV1 영상 **사전 변환 없는 원본 직접 재생**을 위한 권장 조합
- **FFmpeg와 FFprobe**: 컷 저장과 영상 FPS/해상도 확인
- **Git**: 소스 버전 관리
- Docker 사용 안 함. OpenCV/MediaPipe/AI 모델 설치 **불필요** (V1은 수동 컷 편집)

## 2. 처음부터 설치하기 (PowerShell)

아래에서 `D:\stockproj\badminton-video-cutter`를 프로젝트 폴더로 사용합니다.

### 2-1. 새 폴더 만들기

PowerShell을 열어 아래를 차례대로 실행합니다.

```powershell
New-Item -ItemType Directory -Force "D:\stockproj\badminton-video-cutter"
Set-Location "D:\stockproj\badminton-video-cutter"
```

다운로드한 ZIP(`badminton-video-cutter-v1.2.zip`) 안의 **4개 파일**을 이 폴더에 압축 해제합니다. 파일을 직접 저장했다면 네 파일을 해당 폴더에 복사하면 됩니다.

예시: ZIP을 Windows 다운로드 폴더에 저장한 경우

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\badminton-video-cutter-v1.2.zip" -DestinationPath "D:\stockproj\badminton-video-cutter" -Force
Get-ChildItem -Force
```

파일 목록에서 `badminton_video_cutter.py`, `README.md`, `INSTALL.md`, `.gitignore`가 보여야 합니다.

### 2-2. Python 3.12 확인 및 설치

```powershell
py -3.12 --version
```

Python 3.12가 없다면 Windows의 `winget`으로 설치할 수 있습니다.

```powershell
winget install --id Python.Python.3.12 -e
```

설치 후 **PowerShell을 새로 열고** 다시 `py -3.12 --version`으로 확인합니다.

### 2-3. 가상환경 생성·활성화

프로젝트 폴더에서:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

PowerShell 실행 정책 때문에 활성화가 막히면 **가상환경을 활성화하지 않아도 됩니다.** 아래처럼 실행 파일을 직접 사용하세요.

```powershell
.\.venv\Scripts\python.exe --version
```

원한다면 현재 PowerShell 프로세스에서만 활성화 권한을 허용할 수도 있습니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 2-4. PySide6 설치

가상환경이 활성화되었다면:

```powershell
python -m pip install --upgrade pip
python -m pip install PySide6 python-vlc
```

가상환경이 활성화되지 않았다면:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install PySide6
```

### 2-5. VLC 재생 엔진 설치 (AV1 영상 권장)

Windows PowerShell에서 VLC 64비트를 설치합니다 (이미 설치했다면 생략).

```powershell
winget install --id VideoLAN.VLC -e
```

또는 [VLC 공식 Windows 다운로드](https://www.videolan.org/vlc/download-windows.html)에서 **64비트**를 설치하세요. 설치 후 새 PowerShell을 열어 아래 명령을 실행합니다.

```powershell
cd D:\stockproj\badminton-video-cutter
.\.venv\Scripts\python.exe -m pip install python-vlc
Test-Path "C:\Program Files\VideoLAN\VLC\libvlc.dll"
```

`True`이면 일반적인 위치에 VLC 라이브러리가 있습니다. `False`이면 VLC 설치 폴더를 확인하세요. 다른 곳에 설치했다면 이 세션에서 다음을 설정할 수 있습니다.

```powershell
$env:PYTHON_VLC_LIB_PATH = "D:\VLC\libvlc.dll"   # 예시: 실제 경로로 변경
$env:VLC_PLUGIN_PATH = "D:\VLC\plugins"        # 예시: 실제 경로로 변경
```

V1.2는 시작 시 VLC 라이브러리를 검사해 가능한 경우 원본을 재생합니다. Qt 검은 화면 오류를 반복하지 않고 **재생 직후 바로 IN/OUT 작업이 가능합니다.** VLC에서도 CPU AV1 디코딩 성능이 모자라면 끊김이 발생할 수 있습니다.

### 2-5. FFmpeg 설치

일반적으로 아래 명령으로 설치할 수 있습니다.

```powershell
winget install --id Gyan.FFmpeg -e
```

PowerShell을 새로 열어 확인합니다.

```powershell
ffmpeg -version
ffprobe -version
```

인식하지 못하면 환경변수 `PATH` 적용 여부를 확인하거나, 설치한 FFmpeg의 `bin` 폴더에 있는 **`ffmpeg.exe`, `ffprobe.exe`를 프로젝트의 Python 파일과 같은 폴더**에 복사할 수 있습니다. 이 프로그램은 Python 파일과 같은 디렉터리에서 먼저 해당 실행파일을 탐색한 뒤 `PATH`를 확인합니다.

### 2-6. 실행

```powershell
Set-Location "D:\stockproj\badminton-video-cutter"
.\.venv\Scripts\python.exe .\badminton_video_cutter.py
```

가상환경이 활성화되었다면 `python .\badminton_video_cutter.py`도 가능합니다.

## 3. 사용 순서

1. **동영상 열기** 버튼을 눌러 원본 MP4 등을 불러옵니다. **AV1 영상이라면** 먼저 "영상 재생 호환성" 영역에 미리보기 변환 진행률이 표시됩니다. 완료되면 정상 재생할 수 있습니다. (긴 40분 영상은 몇 분~수십 분 이상 소요될 수 있습니다.)
2. 재생/일시정지, 슬라이더 또는 좌우 방향키를 이용해 첫 구간으로 이동합니다.
3. `I` 키로 **IN(시작)** 지정, `O` 키로 **OUT(끝)** 지정합니다.
4. `스트로크 종류`를 선택하고 필요한 경우 `메모`를 입력합니다.
5. **컷 추가** 버튼(또는 `N`)을 눌러 목록에 등록합니다.
6. 필요한 만큼 반복합니다. 목록에서 컷을 선택하면 시작 위치로 이동합니다.
7. **출력 폴더**를 확인하고 **모든 컷 MP4 저장**을 클릭합니다.
8. 출력 폴더에 개별 `.mp4`와 `clips_manifest_*.json`, `clips_manifest_*.csv`가 저장됩니다.
9. 컷을 나중에 다시 편집하려면 **프로젝트 저장**을 사용합니다. `.bcut.json`은 컷 시점과 메모를 저장하지만 영상 자체를 포함하지 않습니다.

영상 재생 중 원하는 위치에서 `I`, `O`를 누를 수 있습니다. 리스트에서 **스트로크 종류**, **메모**를 더블클릭하면 셀을 수정할 수 있습니다. **반복 재생**을 체크하면 목록에서 선택한 컷(선택된 컷이 없으면 IN/OUT 구간)을 반복합니다.

### AV1 / 검은 화면 복구 기능 (v1.2)

1. **VLC 64비트 + python-vlc가 설치된 경우**: AV1 원본 영상을 바로 재생합니다. **40분 전체 미리보기 변환이 자동 시작되지 않습니다.** 로그에 `재생 엔진: VLC 원본 직접 재생 (전체 변환 생략)`이 표시됩니다.
2. **VLC가 없는 경우**: 기존에 생성된 `preview_cache/`의 H.264 미리보기를 찾아 재사용합니다. 캐시가 없으면 원본 AV1을 Qt로 열지 않고, 대체 방법 설치 안내를 표시합니다. **자동 전체 변환은 시작하지 않습니다.**
3. **VLC에서 재생 문제가 발생한 경우**: 기존의 `호환 미리보기 생성 / 사용 (예비 수단)` 버튼을 눌러 FFmpeg 변환 기능을 수동으로 실행할 수 있습니다. 전체 변환은 긴 영상의 경우 오래 걸립니다.
4. **모든 경우**: 컷 추출·메타데이터는 재생용 영상이 아닌 **원본 동영상** 기준입니다. 속도 조절/IN/OUT/로그/프로젝트 저장 등의 기존 기능은 유지됩니다.
5. VLC 환경에서 첫 프레임 표시와 임의 위치 탐색에는 몇 초가 걸릴 수 있습니다. VLC는 프레임 정확성까지 보장하지 않으며 정밀 컷 결과는 재생·검증하세요.

## 4. 단축키

| 단축키 | 기능 |
|---|---|
| `Ctrl+O` | 원본 동영상 열기 |
| `Ctrl+Shift+O` | 저장된 프로젝트 열기 |
| `Ctrl+S` | 프로젝트 저장 |
| `Ctrl+Shift+S` | 프로젝트 다른 이름으로 저장 |
| `Ctrl+E` | 모든 컷 내보내기 |
| `Space` | 재생 / 일시정지 |
| `I` / `O` | IN / OUT 지정 |
| `N` | 컷 목록에 추가 |
| `←` / `→` | FPS 기반 약 1프레임 뒤로 / 앞으로 |
| `Delete` | 컷 목록에 포커스된 상태에서 선택 컷 삭제 |

텍스트 입력 중 문자 단축키가 내용 입력을 가로채지 않도록 처리했습니다.

## 5. 내보내기 방식

| 방식 | 설명 | 권장 용도 |
|---|---|---|
| **정밀 컷 (기본)** | H.264/AAC로 재인코딩, 지정 시각에 더 충실한 편집 | 자세 분석용 학습 영상 |
| **빠른 컷** | 비디오·오디오 스트림 복사, 재인코딩 안 함 | 빠른 미리보기, 대량 컷의 초안 |

**주의:** 빠른 모드는 원본의 키프레임 구조 때문에 시작/끝 시점 오차가 날 수 있습니다. 정밀 모드도 컨테이너 타임스탬프, 가변 FPS, 플레이어 탐색 특성 때문에 **모든 형식에서 완전한 프레임 정확도를 보장하지는 않습니다.** 좌우 키 이동은 FFprobe로 확인한 평균 FPS에 근거한 **시간 간격 근사**입니다. 중요한 구간은 저장한 MP4를 재확인하세요.

원본 파일은 **절대 덮어쓰거나 수정하지 않습니다.** 같은 이름의 컷이 있으면 `_2`, `_3`을 붙여 저장합니다. 실패/취소 시 임시 `.part.mp4`를 정리하고, 이미 완성한 컷은 유지합니다.

## 6. 내보낸 결과 예시

```text
D:\stockproj\badminton-video-cutter\
├─ badminton_video_cutter.py    # 유일한 Python 소스
├─ README.md
├─ INSTALL.md
├─ .gitignore
├─ .venv\                      # 가상환경 (Git 제외)
├─ logs\                       # 실행 로그 (Git 제외)
└─ preview_cache\              # AV1 호환 미리보기 캐시 (Git 제외)

D:\video\lesson_clips\
├─ lesson_001_포핸드_스매시.mp4
├─ lesson_002_오버헤드_클리어.mp4
├─ clips_manifest_20261020_000000_000000.json
└─ clips_manifest_20261020_000000_000000.csv
```

JSON/CSV에는 `source_video`, `clip_file`, `segment_number`, `start_ms`, `end_ms`, `duration_ms`, `label`, `note`, `fps_estimate`, `export_mode` 등을 기록합니다. **성공한 컷만 메타데이터에 포함**하며, 취소/일부 실패 시에도 성공분만 기록합니다.

## 7. Git 시작부터 최초 커밋까지

### 7-1. Git 설치 및 확인

```powershell
git --version
```

없다면:

```powershell
winget install --id Git.Git -e
```

설치 후 PowerShell을 새로 열고 확인합니다.

### 7-2. 프로젝트 폴더에서 저장소 생성

```powershell
Set-Location "D:\stockproj\badminton-video-cutter"
git init -b main
```

Git 사용자 정보가 아직 없다면 *본인이 사용할 이름과 이메일*로 한 번 설정합니다.

```powershell
git config --global user.name "YOUR_NAME"
git config --global user.email "YOUR_EMAIL@example.com"
```

### 7-3. 버전 관리 대상 확인하고 커밋

```powershell
git status
git add .gitignore README.md INSTALL.md badminton_video_cutter.py
git diff --cached --stat
git commit -m "Initial commit: badminton video cutter v1"
git log --oneline -5
```

`.venv`, 로그, 프로젝트 파일, 동영상은 `.gitignore` 규칙으로 Git에 들어가지 않습니다. 동영상 원본·학습 데이터는 큰 파일이므로 별도로 보관하세요.

### 7-4. 이후 수정할 때마다

```powershell
git status
git diff
git add badminton_video_cutter.py README.md INSTALL.md .gitignore
git commit -m "Describe changes"
```

### 7-5. GitHub로 업로드 (선택)

GitHub에서 **빈 저장소** `badminton-video-cutter`를 만든 후, 실제 사용자명으로 주소를 바꾸어 실행합니다. 원격 저장소를 만들지 않았다면 이 단계는 건너뜁니다.

```powershell
git remote add origin https://github.com/YOUR_USERNAME/badminton-video-cutter.git
git push -u origin main
```

## 8. 자주 발생하는 오류

- `No module named 'PySide6'`: 가상환경의 Python으로 실행했는지 확인하고 `.\.venv\Scripts\python.exe -m pip install PySide6` 실행.
- `ffmpeg` / `ffprobe` 명령을 찾지 못함: 설치 경로와 `PATH` 확인, 또는 `.exe` 파일을 Python 소스 옆에 두기.
- AV1 영상이 검게 나오거나 재생되지 않음: 프로그램이 v1.2.0인지 확인하고 `VLC 직접 재생 준비 완료` 로그를 확인하세요. VLC 및 `python-vlc`가 설치되어 있어야 변환 없이 재생합니다. 직접 재생이 실패하면 기존 호환 미리보기 버튼을 사용하세요.
- 프레임 이동 버튼 비활성화: `ffprobe` 실행파일이 없거나 FPS를 확인하지 못한 경우.
- `Git`에서 사용자 정보 설정 요청: `git config --global user.name`, `git config --global user.email` 설정.
- 편집/내보내기 문제: `logs/badminton_video_cutter.log`와 화면 하단 로그 확인.

## 9. 현재 버전 범위와 다음 단계

**V1은 수동 컷 편집기입니다.** 셔틀콕 탐지, 타구 순간 자동 탐지, 스트로크 자동 분류, 랠리 자동 분할, 관절/라켓 각도 계산은 아직 포함되지 않습니다. 해당 기능은 기존 배드민턴 자세 분석기 및 데이터셋 정리 프로그램과 후속 단계에서 연동할 예정입니다.

소스 수정 시에는 기존 UI/기능/로그를 유지하고 필요한 기능만 추가하며, Python 파일 상단에 전체 기능 명세 주석을 갱신합니다.
