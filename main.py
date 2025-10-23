import streamlit as st
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
import plotly.express as px
import pandas as pd
import folium
from streamlit_folium import st_folium
import base64
import openai
import time
import random

# -------------------------------
# 기본 설정
# -------------------------------
st.set_page_config(page_title="서울시 실시간 인구 데이터", page_icon="📊", layout="wide")

# 전체 배경색 노란색
st.markdown("""
    <style>
    body {
        background-color: #fff8dc !important;
        font-family: 'Pretendard', sans-serif;
    }
    .stApp {
        background-color: #fff8dc !important;
    }
    h1, h2, h3 {
        font-family: 'Pretendard', sans-serif;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# 제목
st.markdown("<h1 style='text-align:center; font-size:48px;'>📊 서울시 실시간 인구데이터 분석</h1>", unsafe_allow_html=True)
st.markdown("---")

# -------------------------------
# 사이드바
# -------------------------------
st.sidebar.header("📍 지역 선택")
places_by_district = {
    "강남구": ["강남 MICE 관광특구", "코엑스", "강남역", "선릉역", "역삼역"],
    "종로구": ["광화문·덕수궁", "경복궁", "인사동", "청계천", "서울광장"],
    "마포구": ["홍대 관광특구", "홍대입구역", "연남동", "합정역"],
    "송파구": ["잠실 관광특구", "롯데월드", "석촌호수"],
    "용산구": ["이태원 관광특구", "용산역", "남산타워"],
}
district = st.sidebar.selectbox("구 선택", sorted(places_by_district.keys()))
place = st.sidebar.selectbox("장소 선택", sorted(places_by_district[district]))

# -------------------------------
# API 설정
# -------------------------------
API_KEY = "78665a616473796d3339716b4d446c"
BASE_URL = "http://openapi.seoul.go.kr:8088"
TYPE = "xml"
SERVICE = "citydata_ppltn"

# -------------------------------
# 데이터 로딩 버튼
# -------------------------------
if st.button("🚀 데이터 로딩 시작!"):
    with st.spinner("데이터 불러오는 중... ⏳"):
        time.sleep(2)
        encoded_area = quote(place)
        url = f"{BASE_URL}/{API_KEY}/{TYPE}/{SERVICE}/1/5/{encoded_area}"
        response = requests.get(url)
        root = ET.fromstring(response.content)
        ppltn = root.find(".//SeoulRtd.citydata_ppltn")

    if ppltn is None:
        st.error("⚠️ 데이터를 찾을 수 없습니다.")
    else:
        # 안전 변환 함수
        def safe_int(v): 
            try: return int(v)
            except: return 0
        def safe_float(v):
            try: return float(v)
            except: return 0.0

        area_name = ppltn.findtext("AREA_NM")
        congest_lvl = ppltn.findtext("AREA_CONGEST_LVL")
        congest_msg = ppltn.findtext("AREA_CONGEST_MSG")
        ppltn_min = safe_int(ppltn.findtext("AREA_PPLTN_MIN"))
        ppltn_max = safe_int(ppltn.findtext("AREA_PPLTN_MAX"))
        male = safe_float(ppltn.findtext("MALE_PPLTN_RATE"))
        female = safe_float(ppltn.findtext("FEMALE_PPLTN_RATE"))
        ppltn_time = ppltn.findtext("PPLTN_TIME")

        # -------------------------------
        # ChatGPT API 분석
        # -------------------------------
        client = openai.OpenAI(api_key="YOUR_OPENAI_API_KEY")
        chat_prompt = f"서울시 {area_name}의 현재 혼잡도는 '{congest_lvl}'이고, 인구수는 약 {ppltn_min}~{ppltn_max}명입니다. 관광객에게 어떤 시간대 방문을 추천하겠습니까?"
        chat_response
