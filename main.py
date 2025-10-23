# app.py
import streamlit as st
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from openai import OpenAI
import folium
from streamlit_folium import st_folium
import os
import time

# ================================
# 페이지 기본 설정
# ================================
st.set_page_config(page_title="서울시 실시간 인구", page_icon="📊", layout="wide")

# ================================
# CSS (배경 노란색 + 눈내리는 효과)
# ================================
st.markdown("""
<style>
.stApp {
    background: #fff7cc;
    overflow: hidden;
}
.card {
    background: white;
    border-radius: 18px;
    padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}
.big-congest {
    font-size: 42px;
    font-weight: 700;
    color: #d97706;
    text-align: center;
}
.big-msg {
    font-size: 20px;
    text-align: center;
    margin-bottom: 10px;
}
.snowflake {
    position: fixed;
    top: -10px;
    color: white;
    font-size: 1em;
    animation-name: fall;
    animation-duration: 10s;
    animation-iteration-count: infinite;
}
@keyframes fall {
    0% {top:-10px; opacity:1;}
    100% {top:100vh; opacity:0;}
}
</style>
<div class="snowflake" style="left:10%;">❄</div>
<div class="snowflake" style="left:30%;">❄</div>
<div class="snowflake" style="left:50%;">❄</div>
<div class="snowflake" style="left:70%;">❄</div>
<div class="snowflake" style="left:90%;">❄</div>
""", unsafe_allow_html=True)

# ================================
# OpenAI 초기화
# ================================
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def gpt_analysis(area_name, congest_lvl, congest_msg, df_fc):
    if client is None:
        return "ChatGPT API 키가 없습니다."
    text_table = df_fc.to_string(index=False)
    prompt = f"""
서울시 {area_name} 지역의 실시간 혼잡도는 {congest_lvl}입니다.
메시지: {congest_msg}
예상 인구 데이터:
{text_table}

1) 혼잡 원인
2) 완화 방안 3가지
3) 추천 방문 시간대
4) 관광 팁
간결하게 번호로 구분해 주세요.
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":"도시 데이터 분석가로 행동하세요."},
                  {"role":"user","content":prompt}],
        max_tokens=500
    )
    return resp.choices[0].message.content.strip()

# ================================
# 데이터 호출
# ================================
def fetch_data(area):
    API_KEY = "78665a616473796d3339716b4d446c"
    BASE_URL = "http://openapi.seoul.go.kr:8088"
    TYPE = "xml"
    SERVICE = "citydata_ppltn"
    START_INDEX, END_INDEX = 1, 5

    encoded_area = quote(area)
    url = f"{BASE_URL}/{API_KEY}/{TYPE}/{SERVICE}/{START_INDEX}/{END_INDEX}/{encoded_area}"
    r = requests.get(url)
    root = ET.fromstring(r.content)
    return root.find(".//SeoulRtd.citydata_ppltn")

def safe_float(v):
    try: return float(v)
    except: return 0.0
def safe_int(v):
    try: return int(v)
    except: return 0

# ================================
# 장소 선택
# ================================
places = {
    "강남구": ["강남 MICE 관광특구", "코엑스", "강남역"],
    "종로구": ["광화문·덕수궁", "경복궁", "청계천"],
    "마포구": ["홍대 관광특구", "연남동"],
    "송파구": ["잠실 관광특구", "석촌호수"]
}

with st.sidebar:
    st.header("조회 옵션")
    district = st.selectbox("구 선택", sorted(places.keys()))
    place = st.selectbox("장소 선택", places[district])
    load = st.button("📡 데이터 불러오기")

# ================================
# 데이터 로딩 및 표시
# ================================
if load:
    with st.spinner("데이터 불러오는 중... 잠시만 기다려주세요 ❄"):
        time.sleep(1.5)
        ppltn = fetch_data(place)
        if ppltn is None:
            st.error("데이터 없음.")
        else:
            area_name = ppltn.findtext("AREA_NM")
            congest_lvl = ppltn.findtext("AREA_CONGEST_LVL") or "정보없음"
            congest_msg = ppltn.findtext("AREA_CONGEST_MSG") or ""
            ppltn_min = safe_int(ppltn.findtext("AREA_PPLTN_MIN"))
            ppltn_max = safe_int(ppltn.findtext("AREA_PPLTN_MAX"))
            ppltn_time = ppltn.findtext("PPLTN_TIME") or ""

            fcst_rows = []
            for f in ppltn.findall(".//FCST_PPLTN"):
                fcst_rows.append({
                    "시간": f.findtext("FCST_TIME"),
                    "예상인구": safe_int(f.findtext("FCST_PPLTN_MAX"))
                })
            df_fc = pd.DataFrame(fcst_rows) if fcst_rows else pd.DataFrame(
                [{"시간":"현재","예상인구":int((ppltn_min+ppltn_max)/2)}]
            )

            # 혼잡도 이미지 매핑
            level_map = {"여유":1,"보통":3,"붐빔":6,"매우붐빔":7}
            numeric_level = level_map.get(congest_lvl,3)
            img_path = os.path.join("images", f"{numeric_level}.png")

            # GPT 분석
            gpt_text = gpt_analysis(area_name, congest_lvl, congest_msg, df_fc) if client else "GPT 분석 비활성화"

            # ================================
            # 상단 혼잡도 카드
            # ================================
            colA, colB = st.columns([2,1])
            with colA:
                st.markdown(f"<div class='card'><div class='big-congest'>{congest_lvl}</div><div class='big-msg'>{congest_msg}</div></div>", unsafe_allow_html=True)
            with colB:
                if os.path.exists(img_path):
                    st.image(img_path, caption=f"{congest_lvl}", use_container_width=True)
                else:
                    st.info(f"이미지 없음: {img_path}")

            # ================================
            # GPT 결과
            # ================================
            st.markdown(f"<div class='card'><h4>ChatGPT 예측 분석</h4><p>{gpt_text}</p></div>", unsafe_allow_html=True)

            # ================================
            # 탭 (시간대별 인구 / 성별 / 연령대 / 지도)
            # ================================
            tab1, tab2, tab3, tab4 = st.tabs(["시간대별 인구", "성별 비율", "연령대 비율", "위치 지도"])

            with tab1:
                st.subheader("시간대별 인구 변화")
                fig = px.line(df_fc, x="시간", y="예상인구", markers=True,
                              labels={"예상인구":"인구수"}, title="시간대별 인구 예측")
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                male = safe_float(ppltn.findtext("MALE_PPLTN_RATE"))
                female = safe_float(ppltn.findtext("FEMALE_PPLTN_RATE"))
                gender_df = pd.DataFrame({"성별":["남성","여성"],"비율":[male,female]})
                fig_g = px.pie(gender_df, names="성별", values="비율", title="성별 비율", hole=0.3)
                st.plotly_chart(fig_g, use_container_width=True)

            with tab3:
                age_data = {
                    "10대": safe_float(ppltn.findtext("PPLTN_RATE_10")),
                    "20대": safe_float(ppltn.findtext("PPLTN_RATE_20")),
                    "30대": safe_float(ppltn.findtext("PPLTN_RATE_30")),
                    "40대": safe_float(ppltn.findtext("PPLTN_RATE_40")),
                    "50대": safe_float(ppltn.findtext("PPLTN_RATE_50")),
                    "60대": safe_float(ppltn.findtext("PPLTN_RATE_60")),
                    "70대+": safe_float(ppltn.findtext("PPLTN_RATE_70")),
                }
                age_df = pd.DataFrame({"연령대":list(age_data.keys()),"비율":list(age_data.values())})
                fig_a = px.bar(age_df, x="연령대", y="비율", title="연령대 비율(%)")
                st.plotly_chart(fig_a, use_container_width=True)

            with tab4:
                coords = {
                    "강남 MICE 관광특구": (37.508, 127.060),
                    "광화문·덕수궁": (37.5665,126.9779),
                    "홍대 관광특구": (37.5563,126.9239),
                    "잠실 관광특구": (37.5145,127.1056),
                }
                lat, lon = coords.get(area_name, (37.5665,126.9780))
                m = folium.Map(location=[lat, lon], zoom_start=15)
                folium.Marker([lat, lon], popup=f"{area_name} - {congest_lvl}").add_to(m)
                st_folium(m, width=900, height=450)
