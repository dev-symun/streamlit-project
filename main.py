import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from urllib.parse import quote

# -------------------------------
# 기본 설정
# -------------------------------
st.set_page_config(page_title="서울시 실시간 인구 데이터", page_icon="📊", layout="wide")
st.title("📊 서울시 실시간 인구 데이터 (citydata_ppltn)")

# -------------------------------
# API 설정
# -------------------------------
API_KEY = "78665a616473796d3339716b4d446c"
BASE_URL = "http://openapi.seoul.go.kr:8088"
TYPE = "xml"
SERVICE = "citydata_ppltn"
START_INDEX = 1
END_INDEX = 200  # 충분히 큰 값으로 모든 장소 가져오기

# -------------------------------
# 1️⃣ 전체 장소 목록 가져오기
# -------------------------------
@st.cache_data
def get_all_places():
    url = f"{BASE_URL}/{API_KEY}/{TYPE}/{SERVICE}/{START_INDEX}/{END_INDEX}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    citydata = root.findall(".//SeoulRtd.citydata_ppltn")
    
    places = []
    for c in citydata:
        area_name = c.findtext("AREA_NM")
        area_code = c.findtext("AREA_CD")
        if area_name and area_code:
            places.append({"AREA_NM": area_name, "AREA_CD": area_code})
    
    if not places:
        return pd.DataFrame(columns=["AREA_NM", "AREA_CD"])
    
    return pd.DataFrame(places)

# -------------------------------
# 장소 데이터 불러오기
# -------------------------------
try:
    places_df = get_all_places()
except Exception as e:
    st.error(f"장소 목록 로딩 실패: {e}")
    st.stop()

if places_df.empty:
    st.error("장소 목록이 없습니다.")
    st.stop()

# -------------------------------
# 2️⃣ 사용자 선택 (selectbox)
# -------------------------------
st.markdown("서울시 주요 장소를 선택하세요")
area = st.selectbox("장소 선택", sorted(places_df["AREA_NM"].unique()))
