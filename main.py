# main.py (핵심만 발췌된 완전한 예시)
import streamlit as st
import requests, xml.etree.ElementTree as ET
from urllib.parse import quote
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import time, random, os

# OpenAI v1 client
from openai import OpenAI
from openai.error import AuthenticationError

st.set_page_config(page_title="서울시 실시간 인구데이터 분석", layout="wide")

# 배경 노란색(전역) + 흩어지는 눈 JS/CSS
st.markdown("""
<style>
body { background: #FFF8DC; }
.snowflake { position: fixed; top: -10px; pointer-events: none; z-index:9999; }
</style>
<script>
(function(){
  const count = 40;
  for (let i=0;i<count;i++){
    const s = document.createElement('div');
    s.className='snowflake';
    s.textContent='❄';
    // 랜덤 위치/크기/속도/불투명도
    s.style.left = Math.random()*100 + 'vw';
    s.style.fontSize = (14 + Math.random()*36) + 'px';
    s.style.opacity = (0.4 + Math.random()*0.7);
    s.style.animation = `fall ${4 + Math.random()*8}s linear ${Math.random()*2}s infinite`;
    s.style.transform = `translateX(${(Math.random()-0.5)*200}px)`;
    document.body.appendChild(s);
  }
})();
</script>
<style>
@keyframes fall { 0% { transform: translateY(-10vh); } 100% { transform: translateY(110vh); } }
</style>
""", unsafe_allow_html=True)

# 사이드바: 지역/관광지 + 로딩 버튼
places_by_district = {
    "강남구": ["코엑스","강남역"],
    "종로구": ["광화문·덕수궁","경복궁"],
    "마포구": ["홍대 관광특구","망원한강공원"],
}
st.sidebar.header("조회 옵션")
district = st.sidebar.selectbox("구 선택", sorted(places_by_district.keys()))
place = st.sidebar.selectbox("장소 선택", places_by_district[district])
load_button = st.sidebar.button("🚀 데이터 로딩 시작!")

# OpenAI 키(우선 st.secrets, 없으면 env)
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY") if "OPENAI_API_KEY" in st.secrets else os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# 데이터 불러오기 및 세션 유지
def fetch_and_store(place):
    API_KEY = "78665a616473796d3339716b4d446c"
    BASE_URL = "http://openapi.seoul.go.kr:8088"
    T = "xml"
    SERVICE = "citydata_ppltn"
    url = f"{BASE_URL}/{API_KEY}/{T}/{SERVICE}/1/5/{quote(place)}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    node = root.find(".//SeoulRtd.citydata_ppltn")
    st.session_state['ppltn_node'] = node

if load_button:
    with st.spinner("데이터 로딩 중..."):
        try:
            fetch_and_store(place)
            st.session_state['loaded'] = True
        except Exception as e:
            st.session_state['loaded'] = False
            st.error("데이터 불러오기 실패: " + str(e))

# 화면 출력 (데이터 존재 시)
if st.session_state.get('loaded'):
    node = st.session_state.get('ppltn_node')
    area_name = node.findtext("AREA_NM") or place
    congest_lvl = node.findtext("AREA_CONGEST_LVL") or "정보없음"
    ppltn_min = node.findtext("AREA_PPLTN_MIN") or "0"
    ppltn_max = node.findtext("AREA_PPLTN_MAX") or "0"

    # 상단: 혼잡도 텍스트 + 이미지 (이미지 파일은 images/1..7.png)
    st.markdown(f"## {area_name} — 현재 혼잡도: **{congest_lvl}**")
    # 매핑 로직 예시
    map_level_to_img = {"여유":"1","보통":"4","혼잡":"7"}
    img_idx = map_level_to_img.get(congest_lvl, "4")
    img_path = f"images/{img_idx}.png"
    if os.path.exists(img_path):
        st.image(img_path, width=240)

    # ChatGPT 분석 — 안전하게 처리
    gpt_result = None
    if client is None:
        st.warning("ChatGPT 키가 설정되어 있지 않아 AI 분석을 생략합니다. (st.secrets/OPENAI_API_KEY 필요)")
    else:
        prompt = f"{area_name} 현재 혼잡도: {congest_lvl}. 인구: {ppltn_min}~{ppltn_max}. 개선방안과 추천 시간대 2개를 간단히 써줘."
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role":"system","content":"당신은 도시 데이터 분석 전문가입니다."},
                    {"role":"user","content":prompt}
                ],
                max_tokens=400
            )
            # 안전하게 변수 설정
            gpt_result = resp.choices[0].message.content.strip() if resp and resp.choices else None
        except AuthenticationError as auth_e:
            # 인증 관련 에러는 사용자에게 키 설정 방법 안내
            st.error("OpenAI 인증 실패: OPENAI API 키가 없거나 잘못되었습니다. st.secrets에 OPENAI_API_KEY 또는 환경변수 OPENAI_API_KEY를 설정하세요.")
        except Exception as ex:
            st.error("AI 호출 중 오류가 발생했습니다.")
    if gpt_result:
        st.success(gpt_result)

    # 탭: 성별(원형), 연령대, 시간대별, 지도
    tab1, tab2, tab3, tab4 = st.tabs(["성별(원형)", "연령대", "시간대별(선)", "지도"])
    with tab1:
        male = float(node.findtext("MALE_PPLTN_RATE") or 0)
        female = float(node.findtext("FEMALE_PPLTN_RATE") or 0)
        df_gender = pd.DataFrame({"성별":["남성","여성"], "비율":[male,female]})
        fig = px.pie(df_gender, names='성별', values='비율', hole=0.25, title="성별 비율")
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        labels = ["0대","10대","20대","30대","40대","50대","60대","70대"]
        cols = ["PPLTN_RATE_0","PPLTN_RATE_10","PPLTN_RATE_20","PPLTN_RATE_30","PPLTN_RATE_40","PPLTN_RATE_50","PPLTN_RATE_60","PPLTN_RATE_70"]
        vals = [float(node.findtext(c) or 0) for c in cols]
        df_age = pd.DataFrame({"연령대":labels,"비율":vals})
        st.plotly_chart(px.bar(df_age, x="연령대", y="비율", title="연령대별 비율"), use_container_width=True)
    with tab3:
        fcst_rows = []
        for f in node.findall(".//FCST_PPLTN"):
            fcst_rows.append({"시간": f.findtext("FCST_TIME"), "예상": float(f.findtext("FCST_PPLTN_MAX") or 0)})
        if fcst_rows:
            df_fc = pd.DataFrame(fcst_rows)
            st.plotly_chart(px.line(df_fc, x="시간", y="예상", markers=True, title="시간대별 예상 인구"), use_container_width=True)
        else:
            st.info("예측 데이터 없음.")
    with tab4:
        coords = {"광화문·덕수궁":(37.5665,126.9779)}
        lat, lon = coords.get(area_name, (37.5665,126.9780))
        m = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker([lat, lon], popup=area_name).add_to(m)
        st_folium(m, width=700, height=420)
else:
    st.info("왼쪽에서 지역/관광지 선택 후 '데이터 로딩 시작!' 버튼을 눌러주세요.")
