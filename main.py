import streamlit as st
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

# -------------------------------
# 기본 설정
# -------------------------------
st.set_page_config(page_title="서울시 실시간 인구 데이터", page_icon="📊", layout="wide")
st.title("📊 서울시 실시간 인구 데이터 (citydata_ppltn)")

# -------------------------------
# 서울시 구별 장소 매핑 (예시)
# -------------------------------
places_by_district = {
    "강남구": ["강남 MICE 관광특구", "코엑스", "강남역", "선릉역", "역삼역", "압구정로데오거리", "삼성역"],
    "종로구": ["광화문·덕수궁", "경복궁", "보신각", "창덕궁·종묘", "북촌한옥마을", "덕수궁길·정동길", "인사동", "청계천", "서울광장"],
    "마포구": ["홍대 관광특구", "홍대입구역", "망원한강공원", "상수역", "연남동", "합정역"],
    "용산구": ["이태원 관광특구", "용산역", "남산타워", "이태원역", "국립중앙박물관·용산가족공원", "이태원 앤틱가구거리"],
    "송파구": ["잠실 관광특구", "롯데월드", "잠실역", "석촌호수", "잠실종합운동장", "잠실한강공원", "잠실새내역"],
    "영등포구": ["여의도", "영등포 타임스퀘어", "여의도한강공원", "63빌딩"],
}

# -------------------------------
# 1️⃣ 구 선택
# -------------------------------
district = st.selectbox("구 선택", sorted(places_by_district.keys()))

# -------------------------------
# 2️⃣ 선택한 구의 장소 선택
# -------------------------------
place = st.selectbox("장소 선택", sorted(places_by_district[district]))

# -------------------------------
# API 설정
# -------------------------------
API_KEY = "78665a616473796d3339716b4d446c"
BASE_URL = "http://openapi.seoul.go.kr:8088"
TYPE = "xml"
SERVICE = "citydata_ppltn"
START_INDEX = 1
END_INDEX = 5

# -------------------------------
# 3️⃣ 선택한 장소 API 호출
# -------------------------------
if st.button("📡 데이터 불러오기"):
    try:
        encoded_area = quote(place)
        url = f"{BASE_URL}/{API_KEY}/{TYPE}/{SERVICE}/{START_INDEX}/{END_INDEX}/{encoded_area}"
        response = requests.get(url, timeout=10)
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
            
            st.subheader(f"📍 {area_name} (업데이트: {ppltn_time})")
            col1, col2 = st.columns(2)
            col1.metric("혼잡도", congest_lvl)
            col2.metric("현재 인구 (명)", f"{ppltn_min:,} ~ {ppltn_max:,}")
            st.info(congest_msg)
            
            # -------------------------------
            # 성별 비율 원그래프
            # -------------------------------
            st.write("### 👥 성별 비율")
            labels = ["남성", "여성"]
            sizes = [male, female]
            colors = ['skyblue', 'lightpink']
            
            fig, ax = plt.subplots()
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
            ax.axis('equal')
            st.pyplot(fig)
            
            # 가장 많은 성별
            dominant_gender = "남성" if male > female else "여성"
            st.info(f"💡 현재 인구에서 가장 많은 성별: {dominant_gender}")
            
            # -------------------------------
            # 예측 인구 데이터
            # -------------------------------
            fcst_data = []
            for f in ppltn.findall(".//FCST_PPLTN"):
                fcst_data.append({
                    "시간": f.findtext("FCST_TIME"),
                    "혼잡도": f.findtext("FCST_CONGEST_LVL"),
                    "예상 최소 인구": int(f.findtext("FCST_PPLTN_MIN")),
                    "예상 최대 인구": int(f.findtext("FCST_PPLTN_MAX"))
                })
            if fcst_data:
                import pandas as pd
                df = pd.DataFrame(fcst_data)
                st.write("### ⏰ 시간대별 인구 예측")
                st.dataframe(df)
                st.line_chart(df.set_index("시간")[["예상 최소 인구", "예상 최대 인구"]])
            
            # -------------------------------
            # Folium 지도 표시
            # -------------------------------
            st.write("### 🗺️ 위치 지도")
            coords = {
                "광화문·덕수궁": (37.5665, 126.9779),
                "강남 MICE 관광특구": (37.508, 127.060),
                "홍대 관광특구": (37.5563, 126.9239),
                "잠실 관광특구": (37.5145, 127.1056),
                "용산역": (37.5294, 126.9646),
            }
            lat, lon = coords.get(area_name, (37.5665, 126.9780))
            m = folium.Map(location=[lat, lon], zoom_start=15)
            folium.Marker([lat, lon], popup=area_name).add_to(m)
            st_folium(m, width=700, height=500)
            
    except Exception as e:
        st.error(f"데이터 조회 실패: {e}")
