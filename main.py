import streamlit as st
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
import openai
from datetime import datetime

# -------------------------------
# 기본 설정
# -------------------------------
st.set_page_config(page_title="서울시 실시간 인구 데이터", page_icon="📊", layout="wide")

st.markdown(
    """
    <h1 style="text-align:center;">📊 서울시 실시간 인구 데이터 대시보드</h1>
    <p style="text-align:center; color:gray;">실시간 인구 현황, 예측, AI 요약까지 한눈에 보기</p>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# ChatGPT API 설정
# -------------------------------
openai.api_key = st.secrets.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

def summarize_with_gpt(text):
    """ChatGPT API로 요약"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "서울시 실시간 인구 데이터를 간단히 요약해줘."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"요약 실패: {e}"

# -------------------------------
# 지역 목록
# -------------------------------
places_by_district = {
    "강남구": ["강남 MICE 관광특구", "코엑스", "강남역", "선릉역", "역삼역", "압구정로데오거리"],
    "종로구": ["광화문·덕수궁", "경복궁", "보신각", "창덕궁·종묘", "인사동", "청계천"],
    "마포구": ["홍대 관광특구", "홍대입구역", "망원한강공원", "상수역", "연남동"],
    "용산구": ["이태원 관광특구", "용산역", "남산타워", "국립중앙박물관·용산가족공원"],
    "송파구": ["잠실 관광특구", "롯데월드", "석촌호수", "잠실한강공원"],
}

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
# 사용자 입력
# -------------------------------
district = st.selectbox("구 선택", sorted(places_by_district.keys()))
place = st.selectbox("장소 선택", sorted(places_by_district[district]))

if st.button("📡 데이터 불러오기"):
    try:
        encoded_area = quote(place)
        url = f"{BASE_URL}/{API_KEY}/{TYPE}/{SERVICE}/{START_INDEX}/{END_INDEX}/{encoded_area}"
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ppltn = root.find(".//SeoulRtd.citydata_ppltn")

        if ppltn is None:
            st.error("⚠️ 데이터 없음")
        else:
            st.session_state.data = ppltn
            st.session_state.selected_place = place
    except Exception as e:
        st.error(f"오류 발생: {e}")

# -------------------------------
# 데이터 시각화
# -------------------------------
if "data" in st.session_state and st.session_state.data is not None:
    ppltn = st.session_state.data

    def safe_float(v):
        try:
            return float(v)
        except:
            return 0.0

    def safe_int(v):
        try:
            return int(v)
        except:
            return 0

    area_name = ppltn.findtext("AREA_NM")
    congest_lvl = ppltn.findtext("AREA_CONGEST_LVL")
    congest_msg = ppltn.findtext("AREA_CONGEST_MSG")
    ppltn_min = safe_int(ppltn.findtext("AREA_PPLTN_MIN"))
    ppltn_max = safe_int(ppltn.findtext("AREA_PPLTN_MAX"))
    male = safe_float(ppltn.findtext("MALE_PPLTN_RATE"))
    female = safe_float(ppltn.findtext("FEMALE_PPLTN_RATE"))
    ppltn_time = ppltn.findtext("PPLTN_TIME")

    # 색상 효과 (혼잡도 단계별)
    level_color = {
        "여유": "#7CD1A9",
        "보통": "#FFD580",
        "약간 붐빔": "#FFA07A",
        "붐빔": "#FF6F61"
    }.get(congest_lvl, "#A9A9A9")

    st.markdown(f"""
    <div style='background-color:{level_color};padding:15px;border-radius:10px;'>
        <h3>📍 {area_name} (업데이트: {ppltn_time})</h3>
        <b>혼잡도:</b> {congest_lvl} <br>
        <b>인구:</b> {ppltn_min:,} ~ {ppltn_max:,} 명
        <br><br>
        <i>{congest_msg}</i>
    </div>
    """, unsafe_allow_html=True)

    # 성별 비율 차트
    gender_df = pd.DataFrame({"성별": ["남성", "여성"], "비율": [male, female]})
    st.write("### 👥 성별 비율")
    st.plotly_chart(px.pie(gender_df, names='성별', values='비율', color='성별',
                            color_discrete_map={'남성':'#66b3ff','여성':'#ff99cc'},
                            title="성별 비율"), use_container_width=True)

    # 연령대 비율 그래프
    st.write("### 👶 연령대 비율")
    age_data = {
        "0대": safe_float(ppltn.findtext("PPLTN_RATE_0")),
        "10대": safe_float(ppltn.findtext("PPLTN_RATE_10")),
        "20대": safe_float(ppltn.findtext("PPLTN_RATE_20")),
        "30대": safe_float(ppltn.findtext("PPLTN_RATE_30")),
        "40대": safe_float(ppltn.findtext("PPLTN_RATE_40")),
        "50대": safe_float(ppltn.findtext("PPLTN_RATE_50")),
        "60대": safe_float(ppltn.findtext("PPLTN_RATE_60")),
        "70대 이상": safe_float(ppltn.findtext("PPLTN_RATE_70")),
    }
    st.plotly_chart(px.bar(x=list(age_data.keys()), y=list(age_data.values()),
                           labels={"x": "연령대", "y": "비율(%)"},
                           title="연령대별 인구 비율"), use_container_width=True)

    # 예측 인구 그래프 (애니메이션)
    fcst_data = []
    for f in ppltn.findall(".//FCST_PPLTN"):
        fcst_data.append({
            "시간": f.findtext("FCST_TIME"),
            "예상 인구": safe_int(f.findtext("FCST_PPLTN_MAX")),
            "혼잡도": f.findtext("FCST_CONGEST_LVL")
        })
    if fcst_data:
        df_fc = pd.DataFrame(fcst_data)
        fig = px.bar(df_fc, x="시간", y="예상 인구", color="혼잡도",
                     title="시간대별 예상 인구 변화", animation_frame="시간")
        st.plotly_chart(fig, use_container_width=True)

    # 지도 시각화
    st.write("### 🗺️ 지도 보기")
    coords = {
        "광화문·덕수궁": (37.5665, 126.9779),
        "강남 MICE 관광특구": (37.508, 127.060),
        "홍대 관광특구": (37.5563, 126.9239),
        "잠실 관광특구": (37.5145, 127.1056),
        "용산역": (37.5294, 126.9646),
    }
    lat, lon = coords.get(area_name, (37.5665, 126.9780))
    m = folium.Map(location=[lat, lon], zoom_start=15)
    folium.CircleMarker(
        location=[lat, lon],
        radius=max(5, ppltn_max / 10000),
        color=level_color,
        fill=True,
        fill_opacity=0.6,
        popup=f"{area_name}\n{congest_lvl}"
    ).add_to(m)
    st_folium(m, width=700, height=500)

    # 🔹 ChatGPT 요약 버튼
    if st.button("🧠 AI 요약 보기"):
        raw_text = f"{area_name} / 혼잡도 {congest_lvl}, 인구 {ppltn_min}~{ppltn_max}, 남성 {male}%, 여성 {female}%"
        summary = summarize_with_gpt(raw_text)
        st.success(summary)

    # 🔹 TXT 파일로 저장
    txt_content = f"""
[{datetime.now()}] {area_name}
혼잡도: {congest_lvl}
인구: {ppltn_min:,} ~ {ppltn_max:,}
남성: {male}%, 여성: {female}%
메시지: {congest_msg}
"""
    st.download_button("📥 TXT 파일 다운로드", data=txt_content, file_name="서울시_인구데이터.txt")

