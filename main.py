import streamlit as st
import requests
import pandas as pd
import urllib.parse

# ---------------------------------------------
# 🔹 1. 기본 설정
# ---------------------------------------------
API_KEY = st.secrets["API_KEY"]
BASE_URL = "https://openapi.seoul.go.kr:8088"

SEOUL_DISTRICTS = [
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구",
    "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구",
    "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구",
    "종로구", "중구", "중랑구"
]

st.title("🏙 서울시 실시간 인구 데이터 (구별 분류 자동화)")

# ---------------------------------------------
# 🔹 2. API에서 전체 장소 목록 불러오기
# ---------------------------------------------
@st.cache_data
def get_all_places():
    url = f"{BASE_URL}/{API_KEY}/json/citydata_ppltn/1/200"
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    data = res.json()
    # JSON 구조 탐색
    if "SeoulRtd.citydata_ppltn" in data:
        records = data["SeoulRtd.citydata_ppltn"]
    elif "CITYDATA" in data:
        records = data["CITYDATA"]["CITYDATA"]
    else:
        records = []
    df = pd.json_normalize(records)
    return df[["AREA_NM", "AREA_CD"]]

# 장소 데이터 가져오기
places_df = get_all_places()

if places_df.empty:
    st.error("🚫 장소 데이터를 불러오지 못했습니다. API 응답을 확인하세요.")
    st.stop()

# ---------------------------------------------
# 🔹 3. 구 자동 매핑
# ---------------------------------------------
def classify_district(area_name):
    for gu in SEOUL_DISTRICTS:
        if gu.replace("구", "") in area_name:
            return gu
    return "기타"

places_df["district"] = places_df["AREA_NM"].apply(classify_district)

# 구별 장소 리스트 구성
district_places = {
    gu: sorted(list(places_df[places_df["district"] == gu]["AREA_NM"].unique()))
    for gu in SEOUL_DISTRICTS
    if gu in places_df["district"].values
}

# ---------------------------------------------
# 🔹 4. Streamlit UI
# ---------------------------------------------
selected_gu = st.selectbox("📍 먼저 구를 선택하세요", sorted(district_places.keys()))
selected_place = st.selectbox("🏠 장소를 선택하세요", district_places[selected_gu])

# ---------------------------------------------
# 🔹 5. 선택한 장소의 실시간 인구 정보 불러오기
# ---------------------------------------------
if selected_place:
    encoded_area = urllib.parse.quote(selected_place)
    api_url = f"{BASE_URL}/{API_KEY}/json/citydata_ppltn/1/5/{encoded_area}"

    try:
        res = requests.get(api_url, timeout=10)
        res.raise_for_status()
        data = res.json()

        if "SeoulRtd.citydata_ppltn" in data:
            info = data["SeoulRtd.citydata_ppltn"][0]
            st.subheader(f"📊 {selected_place} 실시간 인구 현황")
            st.write(f"• 혼잡도 수준: {info.get('AREA_CONGEST_LVL', '정보 없음')}")
            st.write(f"• 안내 메시지: {info.get('AREA_CONGEST_MSG', '정보 없음')}")
            st.write(f"• 현재 인구 추정: {info.get('AREA_PPLTN_MIN')} ~ {info.get('AREA_PPLTN_MAX')}명")
            st.write(f"• 데이터 갱신 시각: {info.get('PPLTN_TIME')}")
        else:
            st.warning("⚠️ 해당 장소의 실시간 인구 정보가 없습니다.")
    except Exception as e:
        st.error(f"🚫 API 요청 중 오류 발생: {e}")
