# Badminton Video Cutter V1.2 — Windows 설치 및 Git 사용 안내서

> **대상 환경:** Windows 10/11, PowerShell, Python 3.12, PySide6, FFmpeg/FFprobe, Git  
> **프로젝트 경로:** `D:\stockproj\badminton-video-cutter`  
> **실행 소스:** `badminton_video_cutter.py` (Python 파일은 **1개**)  
> **Docker:** 사용하지 않음

이 문서는 프로젝트 폴더 생성부터 설치, 실행, 동영상 컷 저장, Git 첫 커밋 및 GitHub 연결까지 **처음부터 차례로 따라 할 수 있도록** 정리한 가이드입니다. 이미 V1.1을 설치한 경우에는 **14절의 V1.2 업데이트 절차**로 바로 이동하세요.

---

## 1. 설치 파일 다운로드 및 프로젝트 폴더 만들기

1. `badminton-video-cutter-v1.2.zip`을 다운로드합니다.
2. Windows의 **PowerShell**을 실행합니다.
3. 다음 명령을 실행해 작업 폴더를 만듭니다.

```powershell
New-Item -ItemType Directory -Force "D:\stockproj\badminton-video-cutter"
Set-Location "D:\stockproj\badminton-video-cutter"
```

ZIP 파일을 기본 **다운로드** 폴더에 저장했다면 다음 명령으로 바로 압축을 해제합니다.

```powershell
Expand-Archive `
  -LiteralPath "$env:USERPROFILE\Downloads\badminton-video-cutter-v1.2.zip" `
  -DestinationPath "D:\stockproj\badminton-video-cutter" `
  -Force
```

다운로드 위치나 ZIP 이름을 바꿨다면 `-LiteralPath`를 실제 위치에 맞게 수정하세요. PowerShell의 줄 끝에 표시한 백틱(`` ` ``)은 **명령의 줄바꿈 연결 기호**입니다. 한 줄로 입력해도 됩니다.

파일을 확인합니다.

```powershell
Get-ChildItem -Force
```

예상 파일 구조:

```text
D:\stockproj\badminton-video-cutter\
├── badminton_video_cutter.py    # Python 실행 소스 (단 1개)
├── README.md                    # 프로그램 기능 및 사용 설명서
├── INSTALL.md                   # 현재 설치 및 Git 안내서
└── .gitignore                   # Git에서 제외할 파일 규칙
```

**주의:** `.gitignore`는 숨김 파일처럼 보일 수 있으므로 `Get-ChildItem -Force`로 확인합니다.

## 2. Python 3.12 설치 상태 확인

```powershell
py -3.12 --version
```

정상이면 `Python 3.12.x`가 출력됩니다. 설치되어 있지 않으면:

```powershell
winget install --id Python.Python.3.12 -e
```

설치 후 PowerShell을 **새로 열고**, 프로젝트 폴더로 돌아와 Python 버전을 다시 확인합니다.

```powershell
Set-Location "D:\stockproj\badminton-video-cutter"
py -3.12 --version
```

> PC에 Python 3.13도 설치되어 있어도 괜찮습니다. 이 프로젝트는 `py -3.12`를 지정해서 **Python 3.12 전용 가상환경**을 만듭니다.

## 3. Python 가상환경(.venv) 생성

```powershell
Set-Location "D:\stockproj\badminton-video-cutter"
py -3.12 -m venv .venv
```

가상환경의 Python을 직접 확인합니다.

```powershell
.\.venv\Scripts\python.exe --version
```

가상환경 활성화는 **필수가 아닙니다.** 이 안내서에서는 PowerShell 실행 정책 오류를 피하기 위해 Python 실행 파일을 직접 호출합니다.

활성화해서 사용하고 싶다면 다음 명령을 실행할 수 있습니다.

```powershell
.\.venv\Scripts\Activate.ps1
```

PowerShell 실행 정책 때문에 실패하면 활성화하지 않고 다음 단계로 진행하면 됩니다. 불가피하게 활성화해야 한다면 현재 세션에 한해서만 허용할 수 있습니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 4. PySide6 설치

가상환경에 필요한 Python 패키지를 설치합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install PySide6
```

설치 확인:

```powershell
.\.venv\Scripts\python.exe -c "import PySide6; print('PySide6 OK:', PySide6.__version__)"
```

> V1은 수동 컷 편집 프로그램이므로 **OpenCV, MediaPipe, AI 모델을 설치할 필요가 없습니다.**

### 4-1. V1.2 AV1 원본 직접 재생: VLC 설치 (강력 권장)

전체 AV1 영상을 변환하지 않으려면 다음 명령을 **한 번만** 실행하세요. VLC는 Python 모듈이 아니라 별도로 설치하는 **64비트 재생 엔진**입니다.

```powershell
winget install --id VideoLAN.VLC -e
.\.venv\Scripts\python.exe -m pip install python-vlc
```

VLC가 이미 설치되었다면 첫 명령은 생략할 수 있습니다. VLC 설치가 끝나면 PowerShell을 새로 열고, 필요하면 아래 명령으로 설치 경로를 확인합니다.

```powershell
Test-Path "C:\Program Files\VideoLAN\VLC\libvlc.dll"
```

해당 경로가 `False`라면 VLC가 다른 경로에 설치되었는지 확인하세요. 표준 경로 외에는 14절의 `PYTHON_VLC_LIB_PATH` 안내를 참고하세요. VLC 없이도 기존 H.264 캐시 재생/수동 변환 방식은 계속 사용 가능합니다.

## 5. FFmpeg 및 FFprobe 설치

FFmpeg는 컷 저장, FFprobe는 FPS·해상도 등 영상 정보 확인에 사용됩니다.

```powershell
winget install --id Gyan.FFmpeg -e
```

설치 후 **PowerShell을 새로 열어** 다음 명령을 확인합니다.

```powershell
ffmpeg -version
ffprobe -version
```

두 명령 모두 버전 정보가 출력되어야 합니다.

인식되지 않는다면 설치된 FFmpeg 폴더의 `bin`을 시스템 `PATH`에 추가하거나, `ffmpeg.exe`와 `ffprobe.exe`를 `badminton_video_cutter.py`와 **같은 폴더**에 복사하세요. 프로그램은 소스 파일이 있는 폴더를 먼저 확인하고, 이후 `PATH`를 확인합니다.

이때 Windows가 다운받은 실행 파일에 대한 보안 경고를 표시할 수 있으므로 출처가 신뢰 가능한 FFmpeg 설치본인지 확인하세요.

## 6. 프로그램 실행

```powershell
Set-Location "D:\stockproj\badminton-video-cutter"
.\.venv\Scripts\python.exe .\badminton_video_cutter.py
```

프로그램 창이 열리면 설치의 기본 단계가 완료된 것입니다.

실행 중 오류가 발생하면 PowerShell의 오류 메시지와 `logs\badminton_video_cutter.log`를 확인합니다.

## 7. 첫 번째 동영상 컷 만들기

1. **동영상 열기** 버튼으로 MP4 등 원본 동영상을 불러옵니다. VLC가 설치된 경우 AV1도 사전 변환 없이 직접 재생됩니다. (VLC 미설치 시 기존 캐시를 쓰거나 수동 변환 선택 가능)
2. 재생/일시정지, 타임라인 슬라이더 또는 방향키로 원하는 부분을 찾습니다.
3. 컷 시작 위치에서 **IN** 버튼 또는 `I` 키를 누릅니다.
4. 컷 종료 위치에서 **OUT** 버튼 또는 `O` 키를 누릅니다.
5. 스트로크 종류(포핸드 스매시, 오버헤드 클리어 등)를 선택하고 필요한 메모를 입력합니다.
6. **컷 추가** 버튼 또는 `N` 키로 목록에 등록합니다.
7. 다른 구간에서도 IN/OUT 및 컷 추가를 반복합니다.
8. **출력 폴더**를 확인하고 **모든 컷 MP4 저장**을 선택합니다.
9. 출력 폴더에서 컷 MP4와 `clips_manifest_*.json`, `clips_manifest_*.csv` 생성 여부를 확인합니다.
10. 나중에 컷 목록을 계속 편집하려면 **프로젝트 저장**을 이용해 `.bcut.json` 파일을 보관합니다. 이 프로젝트 파일에는 원본 영상 자체가 포함되지 않습니다.

### 주요 단축키

| 단축키 | 기능 |
|---|---|
| `Ctrl+O` | 영상 불러오기 |
| `Ctrl+Shift+O` | 프로젝트 열기 |
| `Ctrl+S` | 프로젝트 저장 |
| `Ctrl+Shift+S` | 프로젝트 다른 이름으로 저장 |
| `Ctrl+E` | 등록한 컷 전체 내보내기 |
| `Space` | 재생 / 일시정지 |
| `I` / `O` | IN / OUT 지정 |
| `N` | 현재 IN/OUT 구간을 컷 목록에 추가 |
| `←` / `→` | 평균 FPS 기준 약 한 프레임씩 이동 |
| `Delete` | 컷 목록에서 선택한 컷 삭제 |

### MP4 저장 방식

| 방식 | 특징 | 추천 용도 |
|---|---|---|
| **정밀 컷 (기본)** | H.264/AAC로 다시 인코딩해 지정 시각에 더 충실 | 자세 분석 및 AI 학습 영상 |
| **빠른 컷** | 기존 스트림을 재인코딩 없이 복사, 키프레임 때문에 시점 오차 가능 | 빠른 확인·초안 |

**원본 동영상은 변경하거나 덮어쓰지 않습니다.** 다만 가변 FPS 영상이나 코덱 특성에 따라 정밀 컷도 완전한 프레임 단위 정확도를 보장하지는 않으므로 결과 파일을 확인하세요.

## 8. Git 설치 및 최초 커밋

### 8-1. Git 설치 확인

```powershell
git --version
```

Git이 없다면 아래 명령으로 설치합니다.

```powershell
winget install --id Git.Git -e
```

설치 후 PowerShell을 다시 열고 `git --version`을 재확인합니다.

### 8-2. Git 저장소 초기화

```powershell
Set-Location "D:\stockproj\badminton-video-cutter"
git init -b main
```

이미 `.git` 폴더가 있다면 기존 Git 기록을 초기화하지 말고 현재 상태를 확인하세요.

```powershell
git status
```

### 8-3. Git 작성자 정보 설정

작성자 정보가 아직 등록되지 않았다면 본인 정보로 설정합니다.

```powershell
git config --global user.name "YOUR_NAME"
git config --global user.email "YOUR_EMAIL@example.com"
```

`YOUR_NAME` 및 `YOUR_EMAIL@example.com`을 실제 사용할 값으로 바꾸세요. 위 명령은 PC의 다른 저장소에도 적용됩니다. 이 프로젝트에만 적용하려면 `--global`을 빼면 됩니다.

### 8-4. 관리 대상만 추가하고 첫 커밋

```powershell
git status
git add .gitignore README.md INSTALL.md badminton_video_cutter.py
git diff --cached --stat
git commit -m "Initial commit: badminton video cutter v1"
git log --oneline -5
```

`.gitignore`에 의해 `.venv/`, 로그, 동영상, `.bcut.json`, 생성된 JSON/CSV 결과는 기본적으로 Git 관리에서 제외됩니다.

> `git add .`를 바로 실행하기보다 최초 커밋 때는 위와 같이 **소스와 문서 파일만 명시적으로 추가**하는 편이 안전합니다.

## 9. 이후 소스 수정과 Git 사용

수정 전후 상태를 확인하고 커밋합니다.

```powershell
Set-Location "D:\stockproj\badminton-video-cutter"
git status
git diff

git add badminton_video_cutter.py README.md INSTALL.md .gitignore
git commit -m "Improve badminton video cutting"
git log --oneline -5
```

실제 수정한 파일만 `git add`해도 됩니다. 기존 기능/GUI/로그는 유지하면서 수정하고, Python 파일 상단의 **전체 기능 설명 주석**도 변경 사항을 반영하도록 갱신합니다.

## 10. GitHub 저장소 연결 (선택)

GitHub 웹사이트에서 `badminton-video-cutter`라는 **빈 저장소**를 먼저 만듭니다. 저장소 생성 화면에서 README 또는 `.gitignore`를 자동 추가하지 않으면 로컬 첫 커밋과 충돌을 피하기 쉽습니다.

그다음 `YOUR_USERNAME`을 실제 GitHub 사용자 이름으로 바꿉니다.

```powershell
Set-Location "D:\stockproj\badminton-video-cutter"
git remote add origin https://github.com/YOUR_USERNAME/badminton-video-cutter.git
git push -u origin main
```

기존에 `origin`이 등록된 경우에는 `git remote -v`로 먼저 확인하세요. 이미 등록되어 있다는 오류가 나면 주소를 확인한 후 필요할 때만 `git remote set-url origin ...`을 사용합니다.

GitHub 인증은 사용자 계정 설정에 따라 브라우저 로그인 또는 인증 도구가 필요할 수 있습니다. **GitHub 계정 비밀번호를 명령 창에 그대로 입력하는 방식은 사용하지 않습니다.**

이후에는 커밋 다음에 다음 명령으로 업로드합니다.

```powershell
git push
```

GitHub 원격 연결 없이 **로컬 Git만 사용해도 정상적으로 버전 관리**할 수 있습니다.

## 11. 설치·실행 오류 해결

| 증상 | 확인 및 해결 |
|---|---|
| `No suitable Python runtime found` | `py -3.12 --version` 확인, 없으면 Python 3.12 설치 후 PowerShell 재실행 |
| `No module named 'PySide6'` | `.\.venv\Scripts\python.exe`가 아닌 시스템 Python을 사용했을 수 있음. 가상환경 Python으로 PySide6 재설치 |
| `Activate.ps1` 실행 정책 오류 | 활성화 생략하고 `.\.venv\Scripts\python.exe` 직접 사용 |
| `ffmpeg`/`ffprobe`를 찾을 수 없음 | 새 PowerShell에서 확인, `PATH` 확인 또는 EXE 두 개를 소스 파일과 동일한 폴더에 배치 |
| 영상이 검게 보이거나 재생 불가 | v1.2.0과 `VLC 직접 재생 준비 완료` 로그 확인. VLC 64비트 + `python-vlc` 설치 권장. 실패 시 호환 미리보기 버튼으로 수동 변환 가능 |
| 방향키 프레임 이동 불가 | `ffprobe` 탐색 및 영상 FPS 조회 상태 확인 |
| `git commit`에서 작성자 정보 오류 | `git config user.name`, `git config user.email` 설정 후 재시도 |
| `git push`에서 인증/권한 오류 | 원격 URL, GitHub 저장소 권한 및 인증 상태 확인 |
| 컷 저장이 실패함 | 출력 폴더 쓰기 권한·남은 디스크 용량·FFmpeg 설치·화면 하단 로그 확인 |

실행 로그 위치:

```text
D:\stockproj\badminton-video-cutter\logs\badminton_video_cutter.log
```

문제 발생 시 **PowerShell 전체 오류 메시지 + 프로그램 하단 로그 + 위 로그 파일**을 함께 확인하는 것이 가장 빠릅니다.

## 12. 현재 V1에서 지원하는 기능 및 향후 개발 범위

| 기능 | 현재 상태 |
|---|---|
| 동영상 불러오기·재생·정지·배속 | 지원 |
| VLC 원본 직접 재생 (전체 인코딩 없음) | **v1.2 추가 / VLC 설치 필요** |
| AV1 → H.264 호환 미리보기 변환·캐시·취소 | **v1.1 유지 / v1.2에서는 수동 대체 기능** |
| IN/OUT 구간 지정 및 구간 반복 재생 | 지원 |
| FPS 기반 전후 프레임 이동(근사) | 지원 |
| 다중 컷 추가·삭제·편집 | 지원 |
| 스트로크 라벨 및 메모 입력 | 지원 |
| 여러 컷 MP4 일괄 저장 | 지원 |
| JSON/CSV 데이터셋 메타데이터 저장 | 지원 |
| 프로젝트 저장·불러오기 | 지원 |
| 실행·오류·내보내기 로그 | 지원 |
| 타구 순간 자동 탐지·자동 컷 생성 | **V2 개발 예정** |
| 셔틀콕·라켓 객체 탐지 및 AI 자세 분석 | **향후 별도 연동 예정** |

현재 버전은 **수동 컷 편집기**입니다. 자동 타구 탐지와 스트로크 자동 분류는 아직 구현되지 않았습니다.

---

### 최종 설치 확인 체크리스트

- [ ] `D:\stockproj\badminton-video-cutter` 폴더에 Python 소스 1개와 문서 3개가 있다.
- [ ] `py -3.12 --version`이 정상 출력된다.
- [ ] `.venv`가 만들어졌고 PySide6가 설치되었다.
- [ ] `ffmpeg -version` 및 `ffprobe -version`이 정상 출력된다.
- [ ] `badminton_video_cutter.py` 실행 시 GUI 창이 나타난다.
- [ ] 샘플 동영상에서 컷을 하나 만들고 MP4 저장을 확인했다.
- [ ] `git log --oneline -5`에서 첫 커밋이 확인된다.
- [ ] (선택) GitHub에 최초 `git push`를 완료했다.


## 13. v1.0 → v1.1 업데이트 (과거 버전 참고 기록)

> 이 절은 이전 v1.1 버전의 설치·변환 방식을 기록한 **이력**입니다. 현재 프로그램 설치/업데이트는 아래 **14절의 V1.2 지침**을 이용하세요.

Windows에서 다음과 같은 오류와 함께 영상이 검게 보일 때 적용하는 버전입니다.

```text
[av1] Your platform doesn't support hardware accelerated AV1 decoding.
[av1] Failed to get pixel format.
[av1] Get current frame error
```

**기존 프로젝트 및 로그 보존**: `.bcut.json` 프로젝트·`logs/`·`.venv/`·내보낸 MP4·원본 영상은 삭제하지 않습니다. Git 커밋이 이미 존재한다면 Git 저장소를 재초기화하지 않습니다.

1. 사용 중인 프로그램을 종료합니다.
2. 제공된 `badminton-video-cutter-v1.1.zip`을 다운로드 폴더에 저장합니다.
3. PowerShell에서 프로젝트로 이동하여 소스 변경 내역을 먼저 확인합니다.

```powershell
cd D:\stockproj\badminton-video-cutter
git status --short
```

4. **기존 Python 파일을 직접 수정해 둔 경우** Git 커밋 또는 복사본으로 먼저 백업합니다. 미수정 상태라면 바로 아래를 실행합니다.

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\badminton-video-cutter-v1.1.zip" -DestinationPath "D:\stockproj\badminton-video-cutter" -Force
```

5. 별도 패키지 추가 설치 없이 기존 `.venv`로 실행합니다.

```powershell
.\.venv\Scripts\python.exe .\badminton_video_cutter.py
```

6. AV1 영상을 열면 **자동 호환 미리보기 변환**이 시작됩니다. 40분 영상은 PC 성능/코덱에 따라 오래 걸릴 수 있습니다. GUI 오른쪽에 진행률과 취소 버튼이 있습니다.
7. 변환된 미리보기는 프로젝트 폴더 아래 `preview_cache/`에 저장되고, **일괄 컷 내보내기는 원본을 사용**합니다.
8. 재생·컷 추가·내보내기를 확인한 뒤 Git 변경사항을 커밋합니다.

```powershell
git status --short
git diff --stat
git add badminton_video_cutter.py README.md INSTALL.md .gitignore
git commit -m "Fix AV1 playback using H264 proxy preview v1.1"
```

**주의:** 변환 완료 전 창을 강제로 종료하지 마세요. 취소 버튼으로 작업을 정리한 후 종료합니다. 필요한 디스크 공간이 부족하면 미리보기가 실패할 수 있습니다. 재생용 캐시를 지워도 원본/컷 결과는 유지됩니다.


## 14. V1.1 → V1.2 업데이트: AV1 즉시 재생 (필독)

40분 AV1 영상의 H.264 미리보기 변환에 20분 넘게 걸리는 문제를 해결하기 위해 **VLC 직접 재생**을 추가했습니다.

### 14-1. 기존 프로젝트 보호

- 기존 `badminton_video_cutter.py`는 업데이트 전 Git 커밋 또는 별도 백업을 남깁니다.
- `.venv/`, `logs/`, `preview_cache/`, `*_clips/`, 기존 `.bcut.json` 프로젝트, 사용자 동영상은 **삭제하지 않습니다**.
- Git 저장소가 이미 있으므로 `git init`을 다시 실행하지 않습니다.

```powershell
cd D:\stockproj\badminton-video-cutter
git status --short
```

### 14-2. VLC 설치 (한 번만 수행)

```powershell
winget install --id VideoLAN.VLC -e
cd D:\stockproj\badminton-video-cutter
.\.venv\Scripts\python.exe -m pip install python-vlc
```

VLC 공식 사이트: https://www.videolan.org/vlc/download-windows.html

VLC 64비트 기본 경로: `C:\Program Files\VideoLAN\VLC\libvlc.dll`.

```powershell
Test-Path "C:\Program Files\VideoLAN\VLC\libvlc.dll"
```

`False`면 설치 위치/비트수를 확인합니다. 비표준 경로에는 다음 환경변수 사용 (경로는 실제 설치 경로로 변경):

```powershell
$env:PYTHON_VLC_LIB_PATH = "D:\VLC\libvlc.dll"
$env:VLC_PLUGIN_PATH = "D:\VLC\plugins"
```

### 14-3. V1.2 파일 적용 및 실행

다운로드한 `badminton-video-cutter-v1.2.zip`을 **기존 폴더에 덮어쓰기**합니다.

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\badminton-video-cutter-v1.2.zip" -DestinationPath "D:\stockproj\badminton-video-cutter" -Force
cd D:\stockproj\badminton-video-cutter
.\.venv\Scripts\python.exe .\badminton_video_cutter.py
```

로그에서 아래 메시지를 확인합니다.

```text
프로그램 시작: v1.2.0
VLC 직접 재생 준비 완료: ...
재생 엔진: VLC 원본 직접 재생 (전체 변환 생략)
동영상 열기: ... 코덱=av1
VLC 원본 직접 재생 준비: ... / 전체 미리보기 변환 생략
```

**영상 열기 후 원본 재생이 바로 준비되는지** 확인합니다. 40분짜리 전체 영상을 H.264로 변환하지 않아야 정상입니다. VLC에서 첫 프레임/임의 탐색이 일시적으로 늦을 수는 있습니다.

### 14-4. 오류 시 확인

- `VLC 직접 재생 비활성` 로그: `python-vlc` 설치 여부 및 `libvlc.dll`의 64비트 설치 경로를 확인합니다.
- 원본이 검게 보일 때: 일반 VLC 앱에서 같은 MP4를 재생해 확인하고, 앱 로그와 VLC 버전을 함께 기록합니다.
- VLC가 없더라도 **기존 `preview_cache/`가 있다면** 앱에서 캐시를 사용합니다. 없을 때는 전체 변환이 자동 시작되지 않고, 호환 미리보기 버튼을 수동으로 눌러야 합니다.
- VLC에서도 CPU AV1 디코딩 성능이 부족하면 끊길 수 있습니다. 미리보기 변환은 원본 컷 내보내기 품질과 무관합니다.

### 14-5. V1.2 변경 사항 Git 기록

```powershell
cd D:\stockproj\badminton-video-cutter
git diff --stat
git add badminton_video_cutter.py README.md INSTALL.md .gitignore
git commit -m "Add direct VLC AV1 playback without full transcode v1.2"
git log --oneline -5
```
