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

# ================================
# 페이지 설정 & 스타일 (배경 노란색)
# ================================
st.set_page_config(page_title="서울시 실시간 인구 데이터(확장판)", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    /* 전체 배경 노란색 */
    .stApp {
        background: #fff7cc;
    }
    /* 카드 스타일 */
    .card {
        background: white;
        padding: 12px;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        margin-bottom: 10px;
    }
    /* 큰 요약 텍스트 */
    .big-summary {
        background: #fff3b0;
        padding: 18px;
        border-radius: 12px;
        font-size: 18px;
        font-weight: 600;
        line-height:1.5;
    }
    /* 버튼 스타일 */
    div.stButton > button {
        background-color: #d97706;
        color: white;
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: 600;
    }
    div.stButton > button:hover {
        background-color: #f59e0b;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ================================
# OpenAI 초기화 (v1.0+ 사용법)
# ================================
# 환경변수/streamlit secrets에 OPENAI_API_KEY를 넣어두세요.
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
if OPENAI_API_KEY is None:
    # key 없으면 버튼 누르면 에러 안내만 표시(요청대로 외부 안내 금지하므로 코드에 주석 처리)
    pass
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def gpt_analysis(area_name, congest_lvl, congest_msg, fcst_df, extra_text=""):
    """GPT를 사용해 혼잡도 분석, 완화방안, 추천 시간대, 관광 팁 생성"""
    if client is None:
        return "ChatGPT 키가 설정되어 있지 않습니다. st.secrets에 OPENAI_API_KEY를 설정하세요."
    # fcst_df를 문자열로 변환 (없으면 안내 문구)
    table_text = fcst_df.to_string(index=False) if (fcst_df is not None and not fcst_df.empty) else "예측 데이터 없음(현재 데이터만 존재)"
    prompt = f"""
당신은 서울시 도시데이터 분석가입니다.
지역: {area_name}
혼잡도: {congest_lvl}
혼잡 메시지: {congest_msg}
시간대별 예측(또는 현재 데이터):
{table_text}

아래 4가지를 한국어로 간결하고 명확히 작성해 주세요.
1) 현재 혼잡도 원인(한두 문장)
2) 혼잡 완화(실행 가능한 3가지 제안, 짧게)
3) 방문 추천 시간대(구체적 시간대 1~2개 및 이유)
4) 관광객 팁 2가지(안전/편의 중심으로)

출력은 번호형식으로 정리해 주세요.
{extra_text}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"도시 데이터 기반 분석가로 행동하세요."},
                {"role":"user","content":prompt}
            ],
            max_tokens=700
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"분석 실패: {e}"

# ================================
# 서울시 구별 장소 매핑 (간단히)
# ================================
places_by_district = {
    "강남구": ["강남 MICE 관광특구", "코엑스", "강남역", "선릉역", "역삼역", "압구정로데오거리"],
    "종로구": ["광화문·덕수궁", "경복궁", "보신각", "창덕궁·종묘", "인사동", "청계천"],
    "마포구": ["홍대 관광특구", "홍대입구역", "망원한강공원", "상수역", "연남동"],
    "용산구": ["이태원 관광특구", "용산역", "남산타워", "국립중앙박물관·용산가족공원"],
    "송파구": ["잠실 관광특구", "롯데월드", "석촌호수", "잠실한강공원"],
    "영등포구": ["여의도", "영등포 타임스퀘어", "여의도한강공원", "63빌딩"]
}

# ================================
# Seoul API 설정
# ================================
API_KEY = "78665a616473796d3339716b4d446c"
BASE_URL = "http://openapi.seoul.go.kr:8088"
TYPE = "xml"
SERVICE = "citydata_ppltn"
START_INDEX = 1
END_INDEX = 5

# ================================
# 세션 초기값
# ================================
if "data" not in st.session_state:
    st.session_state.data = None
if "gpt_result" not in st.session_state:
    st.session_state.gpt_result = None

# ================================
# 사용자 컨트롤 (왼쪽 사이드)
# ================================
with st.sidebar:
    st.header("조회 옵션")
    district = st.selectbox("구 선택", sorted(places_by_district.keys()))
    place = st.selectbox("장소 선택", sorted(places_by_district[district]))
    fetch_btn = st.button("📡 데이터 불러오기")

# ================================
# 데이터 요청 및 파싱
# ================================
def safe_float(v):
    try: return float(v)
    except: return 0.0
def safe_int(v):
    try: return int(v)
    except: return 0

if fetch_btn:
    try:
        encoded_area = quote(place)
        url = f"{BASE_URL}/{API_KEY}/{TYPE}/{SERVICE}/{START_INDEX}/{END_INDEX}/{encoded_area}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ppltn = root.find(".//SeoulRtd.citydata_ppltn")
        if ppltn is None:
            st.error("데이터를 찾을 수 없습니다.")
            st.session_state.data = None
        else:
            st.session_state.data = ppltn
            # 즉시 GPT 분석 실행해서 상단에 크게 보여주기
            # (분석 결과는 화면 상단에 배치)
    except Exception as e:
        st.error(f"데이터 조회 실패: {e}")
        st.session_state.data = None

# ================================
# 화면 상단: ChatGPT 요약 / 예측 (크게)
# ================================
st.markdown("<div class='card'>", unsafe_allow_html=True)

if st.session_state.data is not None:
    ppltn = st.session_state.data
    area_name = ppltn.findtext("AREA_NM")
    congest_lvl = ppltn.findtext("AREA_CONGEST_LVL") or "정보없음"
    congest_msg = ppltn.findtext("AREA_CONGEST_MSG") or ""
    ppltn_min = safe_int(ppltn.findtext("AREA_PPLTN_MIN"))
    ppltn_max = safe_int(ppltn.findtext("AREA_PPLTN_MAX"))
    male = safe_float(ppltn.findtext("MALE_PPLTN_RATE"))
    female = safe_float(ppltn.findtext("FEMALE_PPLTN_RATE"))
    ppltn_time = ppltn.findtext("PPLTN_TIME") or ""

    # 시간대별 예측(FCST_PPLTN)이 있으면 DataFrame 구성
    fcst_rows = []
    for f in ppltn.findall(".//FCST_PPLTN"):
        fcst_rows.append({
            "시간": f.findtext("FCST_TIME"),
            "혼잡도": f.findtext("FCST_CONGEST_LVL"),
            "예상최소": safe_int(f.findtext("FCST_PPLTN_MIN")),
            "예상최대": safe_int(f.findtext("FCST_PPLTN_MAX"))
        })
    if fcst_rows:
        df_fc = pd.DataFrame(fcst_rows)
    else:
        # 예측 데이터가 없으면 현재값으로 선 그래프가 그려지도록 임시 2포인트 생성
        now = datetime.now()
        t0 = now.strftime("%H:%M")
        t1 = (now + timedelta(hours=1)).strftime("%H:%M")
        avg = int((ppltn_min + ppltn_max) / 2) if (ppltn_min or ppltn_max) else 0
        df_fc = pd.DataFrame([
            {"시간": t0, "예상최대": avg},
            {"시간": t1, "예상최대": avg}
        ])

    # GPT 분석 실행 (자동)
    extra = "출력은 간결하게. 각 항목은 번호로 구분."
    gpt_text = gpt_analysis(area_name, congest_lvl, congest_msg, df_fc, extra_text=extra) if client else "ChatGPT 미설정"
    st.session_state.gpt_result = gpt_text

    # 크게 보이기
    st.markdown(f"<div class='big-summary'>{gpt_text}</div>", unsafe_allow_html=True)

else:
    st.markdown("<div class='big-summary'>데이터를 불러오면 지역 분석(혼잡도 개선 제안, 추천 시간대, 관광 팁)을 표시합니다.</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ================================
# 본문 레이아웃: 왼쪽 그래프/오른쪽 카드
# ================================
if st.session_state.data is not None:
    ppltn = st.session_state.data
    area_name = ppltn.findtext("AREA_NM")
    congest_lvl = ppltn.findtext("AREA_CONGEST_LVL") or "정보없음"
    congest_msg = ppltn.findtext("AREA_CONGEST_MSG") or ""
    ppltn_min = safe_int(ppltn.findtext("AREA_PPLTN_MIN"))
    ppltn_max = safe_int(ppltn.findtext("AREA_PPLTN_MAX"))
    male = safe_float(ppltn.findtext("MALE_PPLTN_RATE"))
    female = safe_float(ppltn.findtext("FEMALE_PPLTN_RATE"))
    ppltn_time = ppltn.findtext("PPLTN_TIME") or ""

    # 연령대 데이터
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

    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader(f"시간대별 인구(선 그래프) — {area_name} (업데이트: {ppltn_time})")
        # 시간대별 예상 인구: df_fc을 선그래프로
        # ensure df_fc has column "시간" and "예상최대" or "예상 인구"
        if '예상최대' in df_fc.columns:
            fig = px.line(df_fc, x="시간", y="예상최대", markers=True,
                          labels={"예상최대":"인구수","시간":"시간"},
                          title="시간대별 예상 인구(선 그래프)")
        elif '예상 인구' in df_fc.columns:
            fig = px.line(df_fc, x="시간", y="예상 인구", markers=True,
                          labels={"예상 인구":"인구수","시간":"시간"},
                          title="시간대별 예상 인구(선 그래프)")
        else:
            # 가능성 낮지만 fallback
            numeric_cols = [c for c in df_fc.columns if c != "시간"]
            fig = px.line(df_fc, x="시간", y=numeric_cols, markers=True,
                          title="시간대별 예상 인구(선 그래프)")
        fig.update_layout(transition_duration=200)
        st.plotly_chart(fig, use_container_width=True)

        # 토글: 성별 비율, 연령대 비율
        with st.expander("성별 비율"):
            gender_df = pd.DataFrame({"성별": ["남성","여성"], "비율":[male,female]})
            fig_p = px.pie(gender_df, names='성별', values='비율',
                           title="성별 비율", hole=0.3)
            st.plotly_chart(fig_p, use_container_width=True)

        with st.expander("연령대 비율"):
            age_df = pd.DataFrame({"연령대": list(age_data.keys()), "비율": list(age_data.values())})
            fig_b = px.bar(age_df, x="연령대", y="비율", labels={"연령대":"연령대","비율":"비율(%)"},
                           title="연령대별 비율")
            st.plotly_chart(fig_b, use_container_width=True)

    with col2:
        st.subheader("요약 카드")
        # 혼잡도 점수(가독성용 숫자 매핑)
        # 문자열 혼잡도를 레벨 숫자(1~7)로 매핑하는 임의 규칙
        level_map = {
            "여유":1, "매우여유":1, "거의여유":1,
            "보통":3, "약간 붐빔":4, "붐빔":6, "매우붐빔":7
        }
        numeric_level = level_map.get(congest_lvl, None)
        if numeric_level is None:
            # 문자가 숫자 형태일 수도 있음
            try:
                numeric_level = int(congest_lvl)
            except:
                numeric_level = 3

        # 카드: 추천 시간대 / 혼잡도 점수 / 현재 인구
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"**추천 시간대**")
        # GPT가 준 추천 시간대 추출(간단히 첫 줄에서 찾기) — 안전하게 전체 텍스트 보여줌
        gpt_firstlines = st.session_state.gpt_result.splitlines()[:6] if st.session_state.gpt_result else []
        rec_time = " / ".join([ln for ln in gpt_firstlines if "추천" in ln or "시간대" in ln]) or "GPT 분석 결과 참조"
        st.write(rec_time)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"**혼잡도 점수**")
        st.metric(label=f"혼잡도 ({congest_lvl})", value=f"{numeric_level} / 7")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"**현재 인구(범위)**")
        st.write(f"{ppltn_min:,} ~ {ppltn_max:,} 명")
        st.markdown("</div>", unsafe_allow_html=True)

        # 이미지 표시: images 폴더에서 1~7 이미지 사용
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**혼잡도 이미지**")
        # 이미지 파일 매핑: numeric_level -> images/{n}.png
        img_index = min(max(1, int(numeric_level)), 7)
        img_path = os.path.join("images", f"{img_index}.png")
        if os.path.exists(img_path):
            st.image(img_path, caption=f"혼잡도 비주얼 (레벨 {img_index})", use_column_width=True)
        else:
            st.info(f"이미지 없음: {img_path} (images 폴더에 1~7.png 파일 필요)")
        st.markdown("</div>", unsafe_allow_html=True)

        # API 원본 데이터 다운로드 및 GPT 결과 다운로드
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write("원본 / 결과 저장")
        raw_txt = f"[{datetime.now().isoformat()}] {area_name}\n혼잡도: {congest_lvl}\n인구: {ppltn_min} ~ {ppltn_max}\n남성:{male}%, 여성:{female}%\n메시지:{congest_msg}\n"
        st.download_button("📥 원본 TXT 다운로드", data=raw_txt, file_name=f"{area_name}_raw.txt", mime="text/plain")
        if st.session_state.gpt_result:
            st.download_button("📄 GPT 분석 다운로드", data=st.session_state.gpt_result, file_name=f"{area_name}_analysis.txt", mime="text/plain")
        st.markdown("</div>", unsafe_allow_html=True)

    # 지도를 아래에 배치
    st.write("### 위치 지도")
    coords = {
        "광화문·덕수궁": (37.5665, 126.9779),
        "강남 MICE 관광특구": (37.508, 127.060),
        "홍대 관광특구": (37.5563, 126.9239),
        "잠실 관광특구": (37.5145, 127.1056),
        "용산역": (37.5294, 126.9646),
    }
    lat, lon = coords.get(area_name, (37.5665,126.9780))
    m = folium.Map(location=[lat, lon], zoom_start=15)
    folium.Marker([lat, lon], popup=f"{area_name}\n{congest_lvl}").add_to(m)
    st_folium(m, width=900, height=420)

else:
    st.info("왼쪽 사이드바에서 장소를 선택하고 '데이터 불러오기'를 눌러주세요.")

# ================================
# 하단: 개발 안내 (간단)
# ================================
st.markdown("---")
st.caption("개발: Streamlit 앱 — images/1.png ~ images/7.png 을 프로젝트 폴더의 images 폴더에 넣어주세요.")
