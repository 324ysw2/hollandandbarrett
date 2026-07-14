# 마케팅 개발 아이디어용 논문/자료 모음

이 폴더는 `리뷰/FAQ 기반 브랜드 진단 -> 영업상품 추천 -> PPT/이미지/제안메일 자동화` 개발에 참고할 공개 PDF를 모은 것이다.

## 1. 리뷰 기반 추천 시스템

파일: `review_based_recommender_systems_survey_2024.pdf`

- 원문: https://arxiv.org/abs/2405.05562
- 제목: Review-based Recommender Systems: A Survey of Approaches, Challenges and Future Perspectives
- 쓰임: 리뷰 텍스트를 추천 시스템에 넣는 전체 방법론을 볼 때 가장 먼저 읽기 좋다.
- 네 프로젝트 연결:
  - 브랜드 리뷰/FAQ를 추천 근거로 쓰기
  - 리뷰에서 상품/브랜드 특징 추출
  - 추천 결과에 설명 가능성 붙이기

## 2. 추천 시스템 전체 지도

파일: `comprehensive_review_recommender_systems_2017_2024.pdf`

- 원문: https://arxiv.org/abs/2407.13699
- 제목: A Comprehensive Review of Recommender Systems: Transitioning from Theory to Practice
- 쓰임: 추천 시스템의 전체 흐름, 최신 모델, 실무 적용 방향을 볼 때 좋다.
- 네 프로젝트 연결:
  - 규칙 기반 추천, TF-IDF 유사도, BERT/LLM 추천의 위치 이해
  - 향후 semantic recommender 고도화

## 3. 항목별 감성 분석 Survey

파일: `aspect_based_sentiment_classification_survey_2022.pdf`

- 원문: https://arxiv.org/abs/2203.14266
- 제목: A Survey on Aspect-Based Sentiment Classification
- 쓰임: 리뷰를 단순 긍정/부정이 아니라 `보습`, `진정`, `배송`, `가격` 같은 항목별 감성으로 나누는 방법을 볼 때 좋다.
- 네 프로젝트 연결:
  - `보습/촉촉함`, `진정/장벽`, `가격/혜택`, `배송/CS` 라벨링 고도화
  - 장점/단점 자동 추출 기준 만들기

## 4. ABSA 구현 모델 예시

파일: `absa_gated_convolutional_networks_acl2018.pdf`

- 원문: https://arxiv.org/abs/1805.07043
- 제목: Aspect Based Sentiment Analysis with Gated Convolutional Networks
- 쓰임: 항목별 감성 분석을 모델로 구현하는 예시를 보고 싶을 때 참고.
- 네 프로젝트 연결:
  - 지금은 규칙 기반이지만, 나중에 딥러닝/로컬 모델로 바꿀 때 참고

## 5. B2B 제안서 자동 생성

파일: `generative_ai_b2b_proposal_creation_pricing_2023.pdf`

- 원문: https://www.ijcrt.org/papers/IJCRT23A6008.pdf
- 제목: Generative AI For B2B Proposal Creation And Pricing Optimization
- 쓰임: 제안서 자동 생성, 가격 제안, 영업 자동화 방향성을 볼 때 참고.
- 네 프로젝트 연결:
  - 브랜드별 제안메일/PPT 자동 생성
  - 추천 영업상품별 제안 구조 설계

## 6. 개인화 추천과 프로모션

파일: `personalized_recommendation_customer_self_service_2021.pdf`

- 원문: https://wjarr.com/sites/default/files/fulltext_pdf/WJARR-2021-0391.pdf
- 제목: Personalized recommendation systems for customer self-service and promotions
- 쓰임: 개인화 추천이 고객 경험, 프로모션, 충성도에 어떻게 연결되는지 볼 때 참고.
- 네 프로젝트 연결:
  - 브랜드별 혜택/CRM/리마케팅 제안 근거
  - 제안서에서 기대효과 설명

## 추천 읽는 순서

1. `review_based_recommender_systems_survey_2024.pdf`
2. `aspect_based_sentiment_classification_survey_2022.pdf`
3. `comprehensive_review_recommender_systems_2017_2024.pdf`
4. `generative_ai_b2b_proposal_creation_pricing_2023.pdf`
5. `personalized_recommendation_customer_self_service_2021.pdf`
6. `absa_gated_convolutional_networks_acl2018.pdf`

## 개발 아이디어로 바꾸기

이 논문들을 네 프로젝트에 적용하면 개발 방향은 다음 네 줄로 정리된다.

```text
브랜드 리뷰/FAQ 수집
-> 항목별 감성/구매장벽 분석
-> 유사 브랜드 기반 영업상품 추천
-> PPT/이미지/제안메일 자동 생성
```

다음에 붙이면 좋은 기능:

- 브랜드별 리뷰 근거 신뢰도 점수
- 유사 브랜드 지도 HTML
- 영업상품별 제안서 템플릿
- 추천 결과와 사람이 수정한 결과를 저장하는 학습 데이터
- BERT/sentence-transformer 기반 브랜드 임베딩
