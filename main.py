import streamlit as st
import requests
import pandas as pd
import urllib.parse

# 서울시 25개 구 리스트
SEOUL_DISTRICTS = [
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구",
    "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구",
    "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구",
    "종로구", "중구", "중랑구"
]

API_KEY = st.secrets["API_KEY"]

st.title("📊 서울시 실시간 인구 혼잡도 분석")

# 구 선택
selected_gu = st.selectbox("📍 먼저 구를 선택하세요", sorted(SEOUL_DISTRICTS))

# 구별 대표 장소 목록 (예시 — 실제로는 엑셀 기반 매핑 가능)
district_places = {
    "강남구": ["코엑스", "강남역", "선릉공원"],
    "마포구": ["홍대입구", "망원한강공원", "상수역"],
    "송파구": ["롯데월드", "석촌호수", "잠실역"],
    "용산구": ["남산타워", "이태원", "용산역"],
    "영등포구": ["여의도한강공원", "63빌딩", "타임스퀘어"]
}

places = district_places.get(selected_gu, ["해당 구의 주요 장소 정보 없음"])
selected_place = st.selectbox("🏠 장소를 선택하세요", places)

# API 호출
if "해당 구의 주요 장소 정보 없음" not in selected_place:
    encoded_area = urllib.parse.quote(selected_place)
    API_URL = f"https://openapi.seoul.go.kr/api/{API_KEY}/json/citydata_ppltn/1/100/{encoded_area}"

    try:
        res = requests.get(API_URL, timeout=10)
        data = res.json()

        if "CITYDATA" in data:
            ppltn_data = data["CITYDATA"]["CITYDATA"]
            st.success(f"✅ {selected_place}의 데이터를 성공적으로 불러왔습니다.")
            st.json(ppltn_data)
        else:
            st.warning("⚠️ 해당 장소의 데이터가 없습니다.")
    except Exception as e:
        st.error(f"🚫 API 요청 중 오류 발생: {e}")
