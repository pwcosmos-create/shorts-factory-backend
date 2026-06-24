# 📊 KPI 데이터 요구사항 통합 매핑 시트 (Version 2)

## 🎯 목표: '개인화된 시스템적 통제권(SSI)' 증명 및 월천만원 달성 기반 마련
이 문서는 코다리가 수집한 원시 데이터(`Raw Data`)가 어떤 비즈니스 KPI를 측정하는 데 사용되는지, 그리고 이를 위해 필요한 모든 웹 트래킹 매개변수(Parameters)와 연동되어야 합니다.

---

### 🔗 섹션 A: 핵심 성과 지표 (Business KPIs)
| KPI 명 | 정의 및 목표 가치 | 데이터 출처 | 필수 트래킹 요소 | 측정 주체/담당자 |
| :--- | :--- | :--- | :--- | :--- |
| **LTV (Life Time Value)** | 사용자가 우리 서비스에 머무는 총 예측 가치. *예측 가능성* 증명. | PayPal 매출 데이터 + 사용자 활동 로그 | `user_id`, `first_action_date` | 코다리 / 현빈 |
| **CAC (Customer Acquisition Cost)** | 신규 고객 유입 비용. 광고 소재의 효율성을 측정. | Google/Toss 광고 플랫폼 API | `utm_source`, `utm_medium` | 레오 / 사장님 |
| **SSI Index (통제권 지수)** | 사용자가 데이터 기반으로 '위험을 감소시킨' 행동 횟수. **(핵심 차별화)** | 웹 이벤트 로그, 앱 내 기능 사용 기록 | `event_name=risk_reduced`, `value=X` | Designer / Writer |
| **Conversion Rate (CVR)** | 특정 랜딩 페이지/소재를 본 사용자의 전환율. | 광고 플랫폼 API | `campaign_id`, `landing_page_view` | 레오 / 사장님 |

### ⚙️ 섹션 B: 필수 트래킹 매개변수 정의 (UTM & Event ID)
모든 마케팅 소재와 랜딩 페이지는 아래의 파라미터를 반드시 포함해야 합니다.

1. **UTM Parameters:**
    *   `utm_source`: [필수] 유입 출처 (예: `instagram`, `naver`)
    *   `utm_medium`: [필수] 매체 유형 (예: `reel`, `paid_story`)
    *   `utm_campaign`: [필수] 캠페인 이름/목표 (예: `SSI_Launch_V1`)
2. **Custom Event IDs:**
    *   **Event 1 (통제권 확보):** `event_name=data_validated`, `value=true`. (사용자가 대시보드에서 데이터 검증을 완료했을 때 발생)
    *   **Event 2 (정보 요청):** `event_name=info_requested`, `details=query_type`. (어떤 정보를 궁금해했는지 추적)

### 📝 다음 액션 항목 (Action Items for Agents)
1. **[Writer/현빈]:** 정의된 KPI를 바탕으로, 고객이 '통제권을 얻는 과정'에 대한 서사(Story Flow)의 디테일을 재검토해주세요.
2. **[Designer/레오]:** 필요한 이벤트 ID와 UTM 매개변수를 시각화할 수 있는 인터랙티브 Mockup을 준비해주세요.