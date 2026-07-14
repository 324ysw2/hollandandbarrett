# final_project

화장품 리뷰 데이터에서 제품별 핵심 리뷰 문장과 키워드를 뽑고, KoSentenceBERT로 문장 벡터를 만든 뒤 Elasticsearch에 넣는 파이프라인입니다.

## Pipeline

1. `keyword/key_sentences.py`
   - 화장품 리뷰 CSV를 읽습니다.
   - 제품 단위로 리뷰를 묶습니다.
   - KR-WordRank로 제품별 핵심 키워드와 대표 리뷰 문장을 추출합니다.
   - 결과 CSV를 `data/cosmetic_keysentences_날짜.csv`로 저장합니다.

2. `elastic_util/csv2json.py`
   - 핵심 문장 CSV를 읽습니다.
   - `model/training_stsbenchmark_skt_kobert_model_-2021-03-28_05-25-43_best` 모델로 리뷰 문장을 768차원 벡터로 바꿉니다.
   - Elasticsearch 적재용 JSON을 `data/posts/cosmetic_posts_날짜.json`로 저장합니다.

3. `elastic_util/data_bulk.py`
   - JSON 문서를 Elasticsearch의 `cosmetic_reviews` 인덱스에 bulk 적재합니다.
   - `brand_name`, `product_name`, `category`, `review`, `keywords`, `review_vector` 필드를 사용합니다.

## Expected CSV Columns

기본 자동 탐지 컬럼은 아래 이름들을 우선 사용합니다.

| 목적 | 기본 후보 |
| --- | --- |
| 제품 ID | `PRODUCT_ID`, `product_id`, `상품ID`, `상품번호`, `제품ID`, `item_id`, `id` |
| 제품명 | `PRODUCT_NAME`, `product_name`, `상품명`, `제품명`, `품명`, `name` |
| 브랜드명 | `BRAND_NAME`, `brand_name`, `BRAND`, `brand`, `브랜드명`, `브랜드` |
| 카테고리 | `CATEGORY`, `category`, `카테고리`, `분류`, `대분류`, `소분류` |
| 리뷰 본문 | `REVIEW_TEXT`, `review_text`, `REVIEW`, `review`, `리뷰`, `리뷰내용`, `후기`, `상품평`, `내용`, `comment`, `COMMENT` |

컬럼명이 다르면 실행할 때 직접 지정하면 됩니다.

## Usage

```bat
cd /d C:\projects\company\db\final_project
```

핵심 문장과 키워드 추출:

```bat
python keyword\key_sentences.py --input "C:\path\to\cosmetic_reviews.csv"
```

컬럼명을 직접 지정하는 예시:

```bat
python keyword\key_sentences.py ^
  --input "C:\path\to\cosmetic_reviews.csv" ^
  --product-id-col "상품ID" ^
  --product-name-col "상품명" ^
  --brand-col "브랜드명" ^
  --category-col "카테고리" ^
  --review-col "리뷰내용"
```

문장 벡터 JSON 생성:

```bat
python elastic_util\csv2json.py
```

Elasticsearch 적재:

```bat
python elastic_util\data_bulk.py --recreate
```

## Notes

- `keyword/key_sentences.py`의 stopwords는 화장품 리뷰 기준입니다. `피부`, `제품`, `사용`, `구매`, `배송`, `향`, `크림`, `토너`처럼 너무 흔한 단어는 대표 키워드에서 제외합니다.
- Elasticsearch에서 `nori_tokenizer`를 사용하므로 nori analysis plugin이 필요합니다.
- 기존 음식점용 필드였던 `res_name`, `adress`, `comment_vector`는 화장품용 `brand_name`, `product_name`, `category`, `review_vector` 구조로 바뀌었습니다.
