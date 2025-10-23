import streamlit as st
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import time
import random
from openai import OpenAI

# -------------------------------
# 기본 설정
# -------------------------------
st.set_page_config(page_title="서울시 실시간 인구 데이터", page_icon="📊", layout="wide")

# 배경색 및 폰트 설정
st.markdown("""
    <style>
        body {
            background-color: #FFF8DC;
            font-family: 'Pretendard', sans-serif;
        }
        h1 {
            text-align: center;
            color: #222;
            font-size: 3em;
            margin-top: 0.5em;
        }
        .snowflake {
            color: #87CEFA;
            font-size: 28px;
            position: fixed;
            top: 0;
            z-index: 999;
            animation: fall 10s linear infinite;
        }
        @keyframes fall {
            0% { top: -10px; opacity: 1; }
            100% { top: 100vh; opacity: 0; }
        }
    </style>
""", unsafe_allow_html=True)

st.title("❄️ 서울시 실시간 인구데이터 분석")

# -------------------------------
# 사이드바 설정
# -------------------------------
st.sidebar.header("📍 지역 선택")

places_by_district = {
    "강남구": ["강남 MICE 관광특구", "코엑스", "강남역", "선릉역", "역삼역", "압구정로데오거리", "삼성역"],
    "종로구": ["광화문·덕수궁", "경복궁", "보신각", "창덕궁·종묘", "북촌한옥마을", "덕수궁길·정동길", "인사동", "청계천", "서울광장"],
    "마포구": ["홍대 관광특구", "홍대입구역", "망원한강공원", "상수역", "연남동", "합정역"],
    "용산구": ["이태원 관광특구", "용산역", "남산타워", "이태원역", "국립중앙박물관·용산가족공원", "이태원 앤틱가구거리"],
    "송파구": ["잠실 관광특구", "롯데월드", "잠실역", "석촌호수", "잠실종합운동장", "잠실한강공원", "잠실새내역"],
    "영등포구": ["여의도", "영등포 타임스퀘어", "여의도한강공원", "63빌딩"],
}

district = st.sidebar.selectbox("구 선택", sorted(places_by_district.keys()))
place = st.sidebar.selectbox("장소 선택", sorted(places_by_district[district]))
load_button = st.sidebar.button("🚀 데이터 로딩 시작!")

# -------------------------------
# 데이터 로딩 및 API 요청
# -------------------------------
API_KEY = "78665a616473796d3339716b4d446c"
BASE_URL = "http://openapi.seoul.go.kr:8088"
TYPE = "xml"
SERVICE = "citydata_ppltn"

if load_button:
    with st.spinner("데이터 불러오는 중... 잠시만 기다려주세요."):
        time.sleep(2)
        encoded_area = quote(place)
        url = f"{BASE_URL}/{API_KEY}/{TYPE}/{SERVICE}/1/5/{encoded_area}"
        response = requests.get(url)
        root = ET.fromstring(response.content)
        ppltn = root.find(".//SeoulRtd.citydata_ppltn")

        if ppltn is None:
            st.error("⚠️ 데이터를 찾을 수 없습니다.")
        else:
            # 눈 효과
            snowflakes = "".join(
                [f"<div class='snowflake' style='left:{random.randint(0,100)}%;'>❄</div>" for _ in range(50)]
            )
            st.markdown(snowflakes, unsafe_allow_html=True)
            time.sleep(1)

            # 혼잡도 데이터
            area_name = ppltn.findtext("AREA_NM")
            congest_lvl = ppltn.findtext("AREA_CONGEST_LVL")
            ppltn_min = ppltn.findtext("AREA_PPLTN_MIN")
            ppltn_max = ppltn.findtext("AREA_PPLTN_MAX")

            # ChatGPT API 호출
            client = OpenAI(api_key="YOUR_API_KEY_HERE")
            chat_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "서울시 혼잡도 분석 전문가로 답하라."},
                    {"role": "user", "content": f"{area_name}의 현재 혼잡도는 {congest_lvl}입니다. 인구는 {ppltn_min}~{ppltn_max}명입니다. 혼잡도 개선 방안과 방문 추천 시간을 알려주세요."}
                ]
            )
            suggestion = chat_response.choices[0].message.content

            # 풍선 효과 (혼잡도에 따라 강도 조절)
            if congest_lvl == "여유":
                for _ in range(1):
                    st.balloons()
            elif congest_lvl == "보통":
                for _ in range(2):
                    st.balloons()
            else:
                for _ in range(3):
                    st.balloons()

            # 상단 혼잡도 섹션
            st.markdown(f"## 🧭 {area_name} — 현재 혼잡도: **{congest_lvl}**")
            st.image(f"images/{random.randint(1,7)}.png", width=250)
            st.markdown(f"### 💬 ChatGPT 분석 결과")
            st.success(suggestion)

            # ----------------------------------
            # 데이터 시각화 컨테이너
            # ----------------------------------
            tabs = st.tabs(["성별 비율", "연령대 비율", "시간대별 인구", "지도"])

            with tabs[0]:
                st.subheader("👥 성별 비율")
                male = float(ppltn.findtext("MALE_PPLTN_RATE") or 0)
                female = float(ppltn.findtext("FEMALE_PPLTN_RATE") or 0)
                gender_df = pd.DataFrame({
                    "성별": ["남성", "여성"],
                    "비율": [male, female]
                })
                fig_gender = px.pie(gender_df, names='성별', values='비율',
                                    color_discrete_map={'남성':'skyblue','여성':'lightpink'},
                                    title="성별 인구 비율")
                st.plotly_chart(fig_gender, use_container_width=True)

            with tabs[1]:
                st.subheader("📊 연령대 비율")
                age_cols = [f"PPLTN_RATE_{i}" for i in range(0, 80, 10)]
                age_labels = [f"{i}대" for i in range(0, 80, 10)]
                age_vals = [float(ppltn.findtext(col) or 0) for col in age_cols]
                df_age = pd.DataFrame({"연령대": age_labels, "비율": age_vals})
                fig_age = px.bar(df_age, x="연령대", y="비율", title="연령대별 인구 비율")
                st.plotly_chart(fig_age, use_container_width=True)

            with tabs[2]:
                st.subheader("⏰ 시간대별 인구 변화")
                fcst_data = []
                for f in ppltn.findall(".//FCST_PPLTN"):
                    fcst_data.append({
                        "시간": f.findtext("FCST_TIME"),
                        "예상 인구": float(f.findtext("FCST_PPLTN_MIN") or 0)
                    })
                if fcst_data:
                    df_fcst = pd.DataFrame(fcst_data)
                    fig_line = px.line(df_fcst, x="시간", y="예상 인구", title="시간대별 인구 변화 추이")
                    st.plotly_chart(fig_line, use_container_width=True)
                else:
                    st.info("예측 데이터가 없습니다.")

            with tabs[3]:
                st.subheader("🗺️ 위치 지도")
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
