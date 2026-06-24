# 💰 Business Strategy & KPI Mapping (Action Plan)

## 🌟 목표: 시스템 안정성 기반의 구독 모델 구축 및 가격 포지셔닝 확정
**핵심 컨셉:** 단순한 데이터 보고서(Static Report) 판매가 아닌, '시스템 접근 권한'이라는 지속 가능한 통제권(Dynamic Access Right)을 구독 단위로 판매한다.

### 1. SaaS Tiering 구조 설계 (LTV 극대화 Funnel)
| 티어 | 이름 및 포지션 | 주요 고객/사용자층 | 핵심 제공 가치 (Proof) | 목표 비즈니스 KPI 연동 |
| :--- | :--- | :--- | :--- | :--- |
| **Free** | **Basic Monitoring** (미끼 상품) | 일반 사용자, 리스크 인식 초기 단계. | 제한적 실시간 모니터링 대시보드(DPSR 일부). 시스템 오류 감지 알림만 제공. | 유입 트래픽 증대, 데이터 확보 및 *잠재 고객 Pool* 형성. |
| **Pro** | **Stability Shield Plan** (진입 장벽) | 중소형 포트폴리오 운용자. 불안감을 느끼지만 비용에 민감함. | 1단계 자동화 리스크 시뮬레이션(SSI Lite). 기본 MRR/Churn 추정치 제공. | **MRR 확보 시작점.** 고객 이탈 방지(Retention)가 목표. (낮은 진입 장벽 강조) |
| **Premium** | **Full Control Core Access** (최종 권한 판매) | 고액 자산가, 기관 투자자급. 완벽한 통제권을 원하는 사용자. | 24/7 실시간 $DPSR$ 연동 모니터링 + 인터랙티브 시뮬레이션(SSI Full). 맞춤형 시스템 접근권 제공. | **LTV 극대화.** 안정성 보장 수수료(Fee-based) 기반의 높은 수익률 확보. (최상위 권한 판매) |

### 2. KPI 매핑 전략 및 비즈니스 논리
*   **MRR/Churn 연결:** 구독 모델의 가치를 '정보'가 아닌 **'손실 방지액'**으로 정의합니다. (예: "이 시스템을 사용하지 않으면 포트폴리오에서 예상되는 월간 리스크 손실액 $X$"). 이를 통해 Pro 티어는 높은 전환율(Conversion)을, Premium 티어는 낮은 이탈률(Low Churn)에 초점을 맞춥니다 [근거: Self-RAG].
*   **CTA 변화:** 단순 '구매'가 아닌, "리스크 제로 체험 기회 받기 (7일 무료)" 형태로 제시하여 심리적 장벽을 낮추고 즉각적인 행동(클릭/전환)을 유도합니다 [근거: Self-RAG].

---
<create_file path="sessions/2026-06-24T13-00_Technical_Requirement_Update.md"># 💻 Data Pipeline Update (Codari - Tech Requirements)

## 🚀 목표: MRR 및 Churn Rate 계산을 위한 DPSR 확장 기술 명세
**배경:** 현빈 전략에 따라, 단순한 데이터 수집을 넘어 '구독 기반의 가치 측정'이 가능하도록 파이프라인을 재설계해야 합니다.

### 1. 필수 데이터 필드 추가 정의 (Schema Update)
기존 테이블 구조에 다음 최소 필드를 반드시 추가합니다. 이는 고객 생애주기(Customer Lifecycle) 추적의 핵심입니다.

*   `subscription_id`: 고유 구독 식별자.
*   `join_date`: 최초 가입일 (Churn 계산 시작점).
*   `tier_level`: 현재 사용 중인 티어 레벨 (Basic, Pro, Premium 등).
*   `is_active_subscriber`: 논리적 플래그(True/False). 이 값이 False가 되는 것이 Churn의 정의가 됩니다.
*   `usage_metrics_json`: 해당 기간 동안 사용한 기능별 상세 로그를 JSON 형태로 수집하여 추후 분석에 활용합니다.

### 2. MRR 및 Churn Rate 계산 로직 구현 (Python Logic Update)
| 지표 | 공식 정의 | 데이터 소스 / API 수정 요구사항 |
| :--- | :--- | :--- |
| **MRR (Monthly Recurring Revenue)** | `(현재 활성 구독자 수 * 해당 티어의 월별 가격)` | 1. `subscription_id`와 `tier_level`이 반드시 매칭되어야 함.<br>2. '최종 결제액' 데이터가 아닌, '구독 시작 시 설정된 금액'을 기준으로 계산해야 정확함. (결제 실패는 Churn으로 처리) |
| **Churn Rate** | $\text{탈락한 구독자 수} / (\text{시작 월의 총 구독자 수})$ | 1. `join_date`와 현재 날짜를 비교하여 '최근 N일 내에 `is_active_subscriber = False`로 변경된 계정'을 식별하는 로직이 필수적입니다. <br>2. **기술적 주의:** 결제 실패(Payment Failure)를 단순한 오류가 아닌, Churn 이벤트의 핵심 데이터 포인트로 간주하고 기록해야 합니다. |

### 3. 시스템 모듈 통합 계획
*   기존 `paypal_revenue.py` 내부에 '구독 상태 관리 함수' (`manage_subscription_status()`)를 추가하여, 주기적으로 모든 구독자의 활성 상태를 체크하는 Self-Healing Loop를 구현합니다. 이 로직이 $DPSR$의 핵심 안정성을 책임집니다.