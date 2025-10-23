# main.py
import streamlit as st
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import os
from openai import OpenAI

st.set_page_config(page_title="서울시 실시간 인구데이터 분석", layout="wide")

# -------------------------------
# 전체 배경 노란색
# -------------------------------
st.markdown("""
<style>
body { background: #FFF8DC; font-family: 'Nanum Gothic', sans-serif; }
.balloon { position: fixed; pointer-events: none; z-index:9999; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 사이드바: 구/장소 선택 + 데이터 로딩
# -------------------------------
places_by_district = {
    "강남구": ["강남 MICE 관광특구", "코엑스", "강남역", "선릉역", "역삼역", "압구정로데오거리"],
    "종로구": ["광화문·덕수궁", "경복궁", "보신각", "창덕궁·종묘", "인사동", "청계천"],
    "마포구": ["홍대 관광특구", "홍대입구역", "망원한강공원", "상수역", "연남동"],
    "용산구": ["이태원 관광특구", "용산역", "남산타워", "국립중앙박물관·용산가족공원"],
    "송파구": ["잠실 관광특구", "롯데월드", "석촌호수", "잠실한강공원"],
    "영등포구": ["여의도", "영등포 타임스퀘어", "여의도한강공원", "63빌딩"]
}

st.sidebar.header("조회 옵션")
district = st.sidebar.selectbox("구 선택", sorted(places_by_district.keys()))
place = st.sidebar.selectbox("장소 선택", sorted(places_by_district[district]))
load_button = st.sidebar.button("🚀 데이터 로딩 시작!")

# -------------------------------
# OpenAI 설정
# -------------------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if "ppltn_node" not in st.session_state:
    st.session_state.ppltn_node = None
if "loaded" not in st.session_state:
    st.session_state.loaded = False

# -------------------------------
# 데이터 불러오기 함수
# -------------------------------
def fetch_and_store(place_name):
    API_KEY = "78665a616473796d3339716b4d446c"
    BASE_URL = "http://openapi.seoul.go.kr:8088"
    TYPE = "xml"
    SERVICE = "citydata_ppltn"
    url = f"{BASE_URL}/{API_KEY}/{TYPE}/{SERVICE}/1/5/{quote(place_name)}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    node = root.find(".//SeoulRtd.citydata_ppltn")
    st.session_state.ppltn_node = node

# -------------------------------
# 데이터 로딩
# -------------------------------
if load_button:
    with st.spinner("데이터 로딩 중..."):
        try:
            fetch_and_store(place)
            st.session_state.loaded = True
        except Exception as e:
            st.session_state.loaded = False
            st.error(f"데이터 불러오기 실패: {e}")

# -------------------------------
# 데이터 표시
# -------------------------------
if st.session_state.loaded and st.session_state.ppltn_node is not None:
    node = st.session_state.ppltn_node
    area_name = node.findtext("AREA_NM") or place
    congest_lvl = node.findtext("AREA_CONGEST_LVL") or "정보없음"
    ppltn_min = int(node.findtext("AREA_PPLTN_MIN") or 0)
    ppltn_max = int(node.findtext("AREA_PPLTN_MAX") or 0)
    data_time = node.findtext("PPLTN_TIME") or "정보없음"

    # 혼잡도 색상
    color_map = {"여유":"#3CB371","보통":"#FFD700","혼잡":"#FF4500"}
    congest_color = color_map.get(congest_lvl,"#FFD700")

    # 혼잡도 상단 표시 + 이미지
    st.markdown(f"# 📊 {area_name} — 현재 혼잡도: <span style='color:{congest_color}'>**{congest_lvl}**</span> 🌟", unsafe_allow_html=True)
    st.markdown(f"**데이터 기준 시각:** {data_time}")

    # 혼잡도 이미지
    img_idx = {"여유":"5","보통":"4","혼잡":"7"}.get(congest_lvl,"4")
    img_path = f"images/{img_idx}.png"
    if os.path.exists(img_path):
        st.image(img_path, use_container_width=True)

    # 풍선 애니메이션 (데이터 로딩 완료 후)
    st.markdown(f"""
    <script>
    const count = 15;
    for(let i=0;i<count;i++){{
        const b = document.createElement('div');
        b.className='balloon';
        b.textContent='🎈';
        b.style.left = Math.random()*100 + 'vw';
        b.style.fontSize = '40px';
        b.style.opacity = 0.8;
        b.style.color = '{congest_color}';
        b.style.transition = 'transform 5s linear';
        b.style.transform = 'translateY(100vh)';
        setTimeout(()=>{{ b.style.transform = 'translateY(-10vh)'; }}, i*200);
        document.body.appendChild(b);
    }}
    </script>
    """, unsafe_allow_html=True)

    # ChatGPT 분석
    gpt_result = None
    if client is None:
        st.warning("ChatGPT API 키가 설정되어 있지 않아 AI 분석을 생략합니다.")
    else:
        prompt = f"{area_name} 현재 혼잡도: {congest_lvl}. 인구: {ppltn_min}~{ppltn_max}. 개선방안과 추천 시간대 2개를 간단히 이모티콘과 함께 알려줘."
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role":"system","content":"당신은 도시 데이터 분석 전문가입니다."},
                    {"role":"user","content":prompt}
                ],
                max_tokens=400
            )
            gpt_result = resp.choices[0].message.content.strip() if resp and resp.choices else None
        except Exception as e:
            st.warning(f"ChatGPT API 호출 실패: {e}")
    if gpt_result:
        st.success(f"🤖 AI 분석: {gpt_result}")

    # 탭 메뉴: 성별, 연령대, 시간대별, 지도
    tab1, tab2, tab3, tab4 = st.tabs(["성별(원형)","연령대","시간대별(선)","지도"])

    # 성별 원
