import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import folium
from streamlit_folium import st_folium
from urllib.parse import quote

# -------------------------------
# 기본 설정
# -------------------------------
st.set_page_config(page_title="서울시 실시간 인구 데이터", page_icon="📊", layout="wide")
st.title("📊 서울시 실시간 인구 데이터 (citydata_ppltn)")

# -------------------------------
# API 설정
# -------------------------------
API_KEY = st.secrets["API_KEY"]
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
    resp = requests.get(url)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    citydata = root.findall(".//SeoulRtd.citydata_ppltn")
    # AREA_NM과 AREA_CD 추출
    places = [{"name": c.findtext("AREA_NM"), "code": c.findtext("AREA_CD")} for c in citydata]
    df = pd.DataFrame(places).dropna()
    return df

try:
    places_df = get_all_places()
except Exception as e:
    st.error(f"장소 목록 로딩 실패: {e}")
    st.stop()

# -------------------------------
# 2️⃣ 사용자 선택 (콤보박스)
# -------------------------------
st.markdown("서울시 주요 장소를 선택하세요")
area = st.selectbox("장소 선택", sorted(places_df["name"].unique()))

# -------------------------------
# 3️⃣ 선택한 장소 API 호출
# -------------------------------
if st.button("📡 데이터 불러오기"):
    try:
        encoded_area = quote(area)
        url = f"{BASE_URL}/{API_KEY}/{TYPE}/{SERVICE}/{START_INDEX}/{START_INDEX+4}/{encoded_area}"
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ppltn = root.find(".//SeoulRtd.citydata_ppltn")
        
        if ppltn is None:
            st.error("해당 지역의 데이터를 찾을 수 없습니다.")
        else:
            # 기본 인구 데이터
            area_name = ppltn.findtext("AREA_NM")
            congest_lvl = ppltn.findtext("AREA_CONGEST_LVL")
            congest_msg = ppltn.findtext("AREA_CONGEST_MSG")
            ppltn_min = int(ppltn.findtext("AREA_PPLTN_MIN"))
            ppltn_max = int(ppltn.findtext("AREA_PPLTN_MAX"))
            male = float(ppltn.findtext("MALE_PPLTN_RATE"))
            female = float(ppltn.findtext("FEMALE_PPLTN_RATE"))
            ppltn_time = ppltn.findtext("PPLTN_TIME")
            
            # 데이터 표시
            st.subheader(f"📍 {area_name} (업데이트: {ppltn_time})")
            col1, col2 = st.columns(2)
            col1.metric("혼잡도", congest_lvl)
            col2.metric("현재 인구 (명)", f"{ppltn_min:,} ~ {ppltn_max:,}")
            st.info(congest_msg)
            
            st.write("### 👥 성별 비율")
            st.progress(int(male))
            st.write(f"남성 {male}% / 여성 {female}%")
            
            # 예측 데이터
            fcst_data = []
            for f in ppltn.findall(".//FCST_PPLTN"):
                fcst_data.append({
                    "시간": f.findtext("FCST_TIME"),
                    "혼잡도": f.findtext("FCST_CONGEST_LVL"),
                    "예상 최소 인구": int(f.findtext("FCST_PPLTN_MIN")),
                    "예상 최대 인구": int(f.findtext("FCST_PPLTN_MAX"))
                })
            if fcst_data:
                df = pd.DataFrame(fcst_data)
                st.write("### ⏰ 시간대별 인구 예측")
                st.dataframe(df)
                st.line_chart(df.set_index("시간")[["예상 최소 인구", "예상 최대 인구"]])
            
            # -------------------------------
            # 4️⃣ Folium 지도 표시 (서울 중심 예시)
            # -------------------------------
            m = folium.Map(location=[37.5665, 126.9780], zoom_start=12)
            folium.Marker(
                location=[37.5665, 126.9780], # 서울 중심 좌표, API 좌표 없으므로 임시
                popup=f"{area_name}\n인구: {ppltn_min}~{ppltn_max}",
                tooltip=area_name,
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(m)
            st_folium(m, width=700, height=500)
            
    except Exception as e:
        st.error(f"데이터 조회 실패: {e}")
