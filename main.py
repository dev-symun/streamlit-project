import streamlit as st
import requests
import pandas as pd
import urllib.parse
import urllib3
from requests.exceptions import SSLError, ConnectionError, RequestException

# SSL 경고 숨기기 (verify=False 사용 시 경고 방지)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_KEY = st.secrets["API_KEY"]
BASE_HTTP = "http://openapi.seoul.go.kr:8088"   # <-- HTTP 사용
BASE_HTTPS = "https://openapi.seoul.go.kr:8088" # 백업 (HTTPS 시도 필요하면 사용)

SEOUL_DISTRICTS = [
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구",
    "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구",
    "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구",
    "종로구", "중구", "중랑구"
]

st.title("🏙 서울시 실시간 인구 데이터 (구-장소 자동 매핑 + SSL 오류 처리)")

@st.cache_data
def fetch_places_from_api():
    """전체 장소 목록 가져오기. HTTP 먼저 시도, 실패 시 HTTPS+verify=False로 재시도."""
    # API 호출 범위(충분히 크게)
    start, end = 1, 500
    # URL (json 타입)
    path = f"/{API_KEY}/json/citydata_ppltn/{start}/{end}"
    urls_to_try = [BASE_HTTP + path, BASE_HTTPS + path]

    last_err = None
    for url in urls_to_try:
        try:
            # 기본 요청
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return parse_places_json(data)
        except SSLError as e:
            last_err = e
            # SSL 오류 발생하면 HTTPS에서 verify=False로 한 번 더 시도
            try:
                resp = requests.get(url, timeout=10, verify=False)
                resp.raise_for_status()
                data = resp.json()
                return parse_places_json(data)
            except Exception as e2:
                last_err = e2
                continue
        except (ConnectionError, RequestException) as e:
            last_err = e
            continue

    # 모든 시도 실패하면 예외 발생
    raise RuntimeError(f"API 요청 실패: {last_err}")

def parse_places_json(data):
    """API 응답의 가능한 구조를 안전히 파싱하여 AREA_NM, AREA_CD 반환"""
    # 다양한 응답 키 대응
    candidates = []
    # 1) 구형/문서에서 쓰이는 키
    if isinstance(data, dict):
        # 경우: "SeoulRtd.citydata_ppltn" 키 형태
        for key in ("SeoulRtd.citydata_ppltn", "CITYDATA", "seoulRtd.citydata_ppltn", "CITY_LIST"):
            if key in data:
                candidates = data[key]
                break
        # 경우: 바로 리스트형태
        if not candidates:
            # 찾을만한 리스트가 단일 딕셔너리 내부에 들어있다면 flatten 해보기
            for v in data.values():
                if isinstance(v, list):
                    candidates = v
                    break

    # 후보가 dict(단일 항목)인 경우 리스트로 변환
    if isinstance(candidates, dict):
        # 일부 API는 {"CITYDATA": {"CITYDATA": [ ... ]}} 형태일 수 있음
        # 재탐색
        for v in candidates.values():
            if isinstance(v, list):
                candidates = v
                break
        else:
            candidates = [candidates]

    if not candidates:
        # 마지막 안전 처리: 빈 리스트 반환
        return pd.DataFrame(columns=["AREA_NM", "AREA_CD"])

    # JSON 정규화
    df = pd.json_normalize(candidates)
    # 필요한 컬럼이 없으면 안전히 생성
    if "AREA_NM" not in df.columns:
        # 때때로 'AREA_NM' 대신 'area_nm' 등 소문자일 수 있음
        for alt in df.columns:
            if alt.lower() == "area_nm":
                df = df.rename(columns={alt: "AREA_NM"})
                break
    if "AREA_CD" not in df.columns:
        for alt in df.columns:
            if alt.lower() == "area_cd":
                df = df.rename(columns={alt: "AREA_CD"})
                break

    # 필수 컬럼이 아직 없으면 빈 DataFrame 반환
    if "AREA_NM" not in df.columns:
        return pd.DataFrame(columns=["AREA_NM", "AREA_CD"])

    # 중복 제거, 필요한 컬럼만 반환
    out = df[["AREA_NM"]].copy()
    out["AREA_CD"] = df["AREA_CD"] if "AREA_CD" in df.columns else None
    out = out.drop_duplicates().reset_index(drop=True)
    return out

def map_district(area_name):
    """AREA_NM에서 구 추출. 기본적으로 '구' 포함여부 확인, 없으면 '기타'."""
    if not isinstance(area_name, str):
        return "기타"
    for gu in SEOUL_DISTRICTS:
        # '강남' 같은 형태가 포함되어 있을 수 있으므로 '구' 제거한 텍스트도 검사
        if gu in area_name or gu.replace("구", "") in area_name:
            return gu
    return "기타"

# ----- 메인 실행 -----
try:
    places_df = fetch_places_from_api()
except Exception as e:
    st.error(f"API 호출 실패: {e}")
    # 폴백 더미 데이터 (앱이 멈추지 않도록)
    sample = [
        {"AREA_NM": "코엑스", "AREA_CD": "A1"},
        {"AREA_NM": "강남역", "AREA_CD": "A2"},
        {"AREA_NM": "홍대입구", "AREA_CD": "B1"},
        {"AREA_NM": "롯데월드", "AREA_CD": "C1"},
        {"AREA_NM": "남산타워", "AREA_CD": "D1"},
    ]
    places_df = pd.DataFrame(sample)

# 구 매핑
places_df["district"] = places_df["AREA_NM"].apply(map_district)

# 구별로 장소 리스트 구성
district_places = {}
for gu in SEOUL_DISTRICTS:
    names = sorted(places_df.loc[places_df["district"] == gu, "AREA_NM"].unique())
    if len(names) > 0:
        district_places[gu] = names

# 기타가 있는 경우 포함
others = sorted(places_df.loc[places_df["district"] == "기타", "AREA_NM"].unique())
if others:
    district_places["기타"] = others

if not district_places:
    st.warning("구별 장소 목록이 비어 있습니다. API 응답을 확인하세요.")
    st.stop()

selected_gu = st.selectbox("📍 구 선택", sorted(district_places.keys()))
selected_place = st.selectbox("🏠 장소 선택", district_places[selected_gu])

# 선택한 장소의 상세 데이터 다시 요청 (안전한 방식)
if st.button("조회"):
    encoded_place = urllib.parse.quote(selected_place)
    # 작은 범위 요청 (1~5)
    url = f"http://openapi.seoul.go.kr:8088/{API_KEY}/json/citydata_ppltn/1/5/{encoded_place}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # 가능한 키들 확인 후 가져오기
        info = None
        if isinstance(data, dict):
            for key in ("SeoulRtd.citydata_ppltn", "CITYDATA", "CITYDATA_LIST"):
                if key in data:
                    info = data[key]
                    break
            # 경우에 따라 리스트 내부 첫 요소가 정보일 수 있음
            if info is None:
                # 탐색: 가장 깊은 리스트에서 첫 dict 뽑기
                for v in data.values():
                    if isinstance(v, list) and v:
                        info = v[0]
                        break
        # info가 리스트이면 첫 항목 사용
        if isinstance(info, list):
            info = info[0] if info else None

        if info:
            st.subheader(f"{selected_place} - 실시간 인구")
            st.write(f"혼잡도: {info.get('AREA_CONGEST_LVL')}")
            st.write(f"메시지: {info.get('AREA_CONGEST_MSG')}")
            st.write(f"현재 인구: {info.get('AREA_PPLTN_MIN')} ~ {info.get('AREA_PPLTN_MAX')}")
            st.write(f"데이터 시각: {info.get('PPLTN_TIME')}")
            # 예측(있다면)
            if "FCST_PPLTN" in info:
                st.write("예측 데이터(FCST_PPLTN) 존재")
        else:
            st.warning("해당 장소의 상세 데이터를 찾지 못했습니다.")
    except SSLError:
        st.error("SSL 오류 발생. http로 재시도 중...")
        try:
            resp = requests.get(url.replace("https://", "http://"), timeout=10, verify=False)
            resp.raise_for_status()
            st.success("http(verify=False)로 데이터 받음 — 보안상 임시 처리")
            st.json(resp.json())
        except Exception as e2:
            st.error(f"재시도 실패: {e2}")
    except Exception as e:
        st.error(f"요청 실패: {e}")
