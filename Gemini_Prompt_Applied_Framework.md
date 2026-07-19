# 🚀 상위 1% 유튜버의 제미나이 프롬프트 & 애니메이션 연출 치트키 반영 보고서

본 문서는 유튜버 **에이아이온(AI:ON)**의 상위 1% 제미나이 프롬프트 치트키, 시네마틱 애니메이션 연출 공식, 그리고 **구글 Gemini 조련 가이드북** 내용을 종합적으로 분석하여, **`숏폼공장`** 백엔드 핵심 파이프라인([main.py](file:///c:/커셔/숏폼공장/main.py))의 이미지/비디오 생성 및 대본 구성 엔진에 반영한 내역을 기록한 개발 프레임워크 문서입니다.

---

## 🎯 1. 개요 및 반영 목적

* **기존 문제점:** 
  1. 기존 대본 생성기는 일반 매장 소개용 멘트로 프롬프트가 작성되어 있어 쿠팡 파트너스 구매 전환(CTA)에 적합하지 않았습니다.
  2. 비주얼 프롬프트(이미지/비디오 생성) 역시 '예쁜 제품 이미지' 수준에 머물렀으며, 카메라 구도, 조명, 질감 등의 명확한 연출 설계도가 없어 생성 결과물의 비주얼 일관성과 상업적 임팩트가 부족했습니다.
  3. 이미지 생성 시 AI가 임의로 기괴한 텍스트나 노이즈(외계어)를 그려 렌더링 퀄리티를 해치는 고질적인 문제가 존재했습니다.
* **해결 방안:** 
  - 대본 생성부에 **PAOF 4원칙** 및 **완성형 대본 공식(HOOK-Body-CTA)**을 주입하여 전환율을 고도화했습니다.
  - 이미지/비디오 생성부에 에이아이온의 **6단계 프롬프트 공식** 및 **시네마틱 카메라 무빙 치트키**를 반영하여 고품질 9:16 비주얼 에셋 생성을 통제 가능한 수준으로 격상시켰습니다.
  - **Gemini 조련 가이드북**의 '텍스트 노이즈 방지 네거티브 프롬프트'와 '일관된 캐릭터 상세 묘사 체크리스트'를 적용하여 완성도를 극대화했습니다.

---

## 🔑 2. 최고의 결과를 얻는 프롬프트 4원칙 (PAOF) 적용

| 원칙 | 개념 (PDF 지침) | 코드 내 실제 구현 및 맵핑 방식 |
| :--- | :--- | :--- |
| **P (Persona)** | 특정 전문가의 역할 부여 | 제미나이에게 **"쿠팡 파트너스 구매 전환율을 극대화하는 상위 1% 숏폼 콘텐츠 크리에이터이자 전문 카피라이터"**의 페르소나 부여 |
| **A (Action)** | 명확하고 구체적인 행동 지시 | 지정된 분량(15초/30초)에 맞는 장면 수(3장면/4장면)와 각 장면의 최적 시간 배분 비율(`duration_ratio`) 및 나레이션 작문 지시 |
| **O (Objective)** | 작업의 목표와 맥락 상세 설명 | 홍보할 상품명과 소구점을 기반으로 시청자를 3초 내 홀리는 **HOOK**, 제품 장점 어필, 최종 **댓글/프로필 제휴 링크 클릭 유도**를 명확한 목적지로 제시 |
| **F (Format)** | 결과물 형식 지정 | 데이터 구조의 엄격성을 위해 Pydantic 모델인 `ShortsBlueprint` 스키마(JSON) 규격으로 정확히 응답받도록 고정 |

---

## 🎬 3. 완성형 대본 구성 공식 적용

영상 길이에 따라 최적의 유지율을 낼 수 있도록 씬 구조를 지능적으로 배분했습니다.

### ⏱️ A. 15초 단기 임팩트 숏폼 (3장면 구성)
*   **1장면 (강력한 HOOK - 30%):** 시청자의 문제점이나 궁금증을 유발하는 3초 이내 오프닝 후킹 자막 및 나레이션.
*   **2장면 (핵심 본문 - 40%):** 제품의 핵심 셀링 포인트와 실제 사용 혜택 제시.
*   **3장면 (클로징 및 CTA - 30%):** 한정 혜택을 강조하며 "댓글 링크에서 바로 최저가 혜택을 확인해보세요!"라는 행동 유도 멘트로 마무리.

### ⏱️ B. 30초 설명형 숏폼 (4장면 구성)
*   **1장면 (HOOK 인트로 - 20%):** 일상 속 페인 포인트(Pain Point) 터치 및 시선 고정.
*   **2장면 (본문 소주제 1 - 30%):** 상품의 가장 독보적인 가치 및 특징 제시.
*   **3장면 (본문 소주제 2 - 30%):** 실사용자의 긍정적 반응 또는 가성비 검증 지표 노출.
*   **4장면 (클로징 및 CTA - 20%):** 요약과 함께 고정 댓글 제휴 링크 클릭 유도.

---

## 🎨 4. 시네마틱 애니메이션 및 비주얼 연출 공식 (6단계 프롬프트) 적용

제미나이가 이미지 생성용 `imagen_prompt`를 작성할 때 랜덤박스 같은 무작위 생성을 멈추고, 아래의 **6단계 만능 공식**을 따르도록 프롬프트 제약 조건을 이식했습니다.

### 1) 6단계 비주얼 프롬프트 공식
제미나이는 다음 형식으로 `imagen_prompt`를 완성형 영어로 영작합니다:
`[Style], [Subject], [Action & Pose], [Background & Lighting], [Camera Angle], [Texture & Quality]`

*   **Style (스타일 정의)**: 실사풍의 경우 영화 질감(`Cinematic film still, Shot on 35mm film`), 애니메이션 풍의 경우 픽사 스타일(`Disney Pixar 3D style`)을 선택 적용.
*   **Subject (주체 묘사)**: 제품 및 캐릭터 상세 묘사. 동물 등장 시 반드시 의인화 키워드 `Anthropomorphic`를 사용하고, 브랜드나 상품명이 들어갈 시 `text "TEXT" written on [location]` 공식을 활용하며, 한글의 경우 `written in Korean Hangul` 팁을 병기하도록 유도.
*   **Action & Pose (행동/모션)**: 시선 집중 및 카메라 상호작용 (`Looking at the camera` 등).
*   **Background & Lighting (배경/조명)**: 감성적인 배경과 뽀샤시 조명 (`Sunny cafe, Soft natural lighting` / `Soft diffused lighting, Bright and airy`).
*   **Camera Angle (카메라 연출)**: 인물/제품 몰입을 돕는 `Slow zoom in`, `Extreme close-up`, `Eye-level`.
*   **Texture & Quality (질감/마무리)**: 매끄럽거나 사실적인 표면 처리 (`Authentic skin texture` / `Fluffy fur texture` / `High quality render`).

### 2) 비디오 무빙 사전 적용 (Veo/Luma Ray 용 `veo_prompt`)
이미지를 4초 비디오로 변환할 때 사용할 `veo_prompt`의 모션도 에이아이온 카메라 무빙 사전에 맞추어 정의하도록 강제했습니다.
*   **풍경/배경 웅장함**: `Drone shot`, `Establishing shot`, `Top down view`
*   **인물/제품 몰입감**: `Slow zoom in`, `Extreme close-up`, `Looking at camera`, `Over the shoulder shot`
*   **동적 움직임**: `Tracking shot`, `POV shot`, `Handheld camera style, subtle shake`

---

## 📕 5. 구글 Gemini 조련 가이드북 연계 고도화 규칙

### 1) 텍스트/자막 생성 노이즈 완전 차단 (네거티브 프롬프팅)
*   **문제 사항**: 이미지 생성 AI는 프롬프트에 '자막' 또는 '영상 배경'을 지시하면 그림 내부에 불필요한 알파벳 텍스트나 워터마크, 노이즈를 맘대로 그리는 경향이 있습니다.
*   **조치 내용**: `main.py` 프롬프트 엔진에 네거티브 필터링을 명문화하여, 의도적으로 텍스트 삽입(`text "..."`)을 선언한 장면을 제외하고는 모든 `imagen_prompt` 끝부분에 반드시 아래의 3줄 제약 문구를 자동 병기하도록 강제했습니다.
    ```text
    No on-screen text.
    No subtitles.
    No background music.
    ```

### 2) 일관된 캐릭터 묘사 체크리스트 (Consistency)
*   **조치 내용**: 여러 장면에서 동일한 인물/제품의 일관성이 무너지는 문제를 방지하기 위해, 캐릭터 생성 지시 시 아래의 7대 체크리스트 항목을 매우 구체적으로 작성하도록 프롬프트 가이드라인을 보강했습니다.
    - **7대 항목**: 나이/국적, 얼굴형, 피부 상태, 헤어스타일, 체형/키, 의상 색상/스타일, 표정 및 분위기

---

## 🛠️ 6. 소스코드 반영 상세 ([main.py](file:///c:/커셔/숏폼공장/main.py))

### 1) [ShortsEngine.generate_blueprint](file:///c:/커셔/숏폼공장/main.py#L140) 프롬프트 고도화
실제 제미나이 API 호출 시 사용되는 `prompt` 변수에 **[Visual & Motion Rules]** 섹션을 추가하여 6단계 공식, 텍스트 노이즈 방지 지침 등을 완벽히 명시했습니다:

```python
# AI 영상 퀄리티를 높이기 위한 '6단계 프롬프트 공식' 및 '시네마틱 연출 치트키' 강제화 규칙
visual_rules = (
    "각 장면의 imagen_prompt(이미지 생성용 영어 프롬프트)는 반드시 아래의 [6단계 프롬프트 공식]에 맞추어 쉼표(,)로 구분된 단어들로 작성해줘:\n"
    "1. [Style]: 영상의 장르 및 화풍 정의 (예: 'Cinematic film still, Shot on 35mm film, Soft natural lighting' 또는 'Disney Pixar 3D animation style')\n"
    "2. [Subject]: 주인공/제품 상세 묘사 (의인화된 동물의 경우 'Anthropomorphic [animal]' 필수 사용, 제품 로고/텍스트 노출 시 'text \"[원하는문구]\" written on [위치]' 형식 적용, 한글 텍스트인 경우 뒤에 ', written in Korean Hangul' 추가)\n"
    "3. [Action & Pose]: 캐릭터의 동작 및 구체적인 모션 (예: 'Slow zoom in', 'Looking at the camera', 'Cooking soup')\n"
    "4. [Background & Lighting]: 주변 환경과 조명/분위기 (예: 'Sunny cafe, Soft natural lighting' 또는 'Neon lights, Cyberpunk atmosphere')\n"
    "5. [Camera Angle]: 카메라 앵글 및 연출 (예: 'Drone shot', 'Eye-level', 'Extreme close-up', 'Low angle shot')\n"
    "6. [Texture & Quality]: 마무리 퀄리티 질감 (예: 'Authentic skin texture', 'Fluffy fur texture', 'High quality render')\n\n"
    "또한, 다음 지침을 반드시 준수해줘:\n"
    "- veo_prompt(비디오 변환용 영어 프롬프트)는 정지된 이미지에 자연스럽고 역동적인 무빙을 입힐 수 있도록 구체적인 카메라 모션 키워드만으로 작성해줘. (예: 'Slow zoom in', 'Camera tracking shot', 'Slow elegant panning')\n"
    "- 각 imagen_prompt는 항상 '9:16 vertical aspect ratio'를 포함해야 해.\n"
    "- [★중요 - 텍스트 노이즈 방지]: 이미지 생성 시 AI가 멋대로 이상한 글자나 기호, 악보 등을 그리는 것을 방지하기 위해, 의도적으로 텍스트 노출 지침(text \"...\")을 넣은 경우를 제외하고는 모든 imagen_prompt 끝에 반드시 다음 세 줄의 네거티브 지침을 추가해줘:\n"
    "  'No on-screen text.\n"
    "  No subtitles.\n"
    "  No background music.'"
)
```

---

## 📈 7. 비즈니스 기대 효과

1. **전환율(CVR)의 대폭적인 개선**: 강력한 HOOK 인트로 설계로 초기 3초 이탈률을 방어하며, 명확한 고정 댓글 지칭 CTA를 배치하여 제휴 파트너스 링크 클릭률을 극대화합니다.
2. **비주얼 에셋 품질 향상 (AI 인형 느낌 제거)**: 이미지 생성 시 `Authentic skin texture`, `Soft natural lighting`을 적용하여 어색하고 번들거리는 전형적인 AI 미녀 느낌을 지우고, 자연스러운 시네마틱 감성 숏폼 영상미를 확보합니다.
3. **텍스트 렌더링 무결성**: 쿠팡 파트너스 홍보용 텍스트 삽입 시, `text "..." written on ..., written in Korean Hangul` 공식을 적용해 글자 뭉개짐이나 이상한 외계어 표기를 원천 차단하며, 그 외 배경에서는 `No on-screen text` 규칙으로 불필요한 낙서가 생기지 않도록 방지합니다.
4. **일관된 AI 결과물 품질**: PAOF 구조화와 6단계 공식 가이드라인을 동시에 제공하므로 제미나이 엔진의 작업 결과물 예측 가능성과 성공률이 비약적으로 상승합니다.
