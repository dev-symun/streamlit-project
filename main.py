import streamlit as st
import pandas as pd
import plotly.express as px
import time
from openai import OpenAI

# -------------------------------
# 페이지 기본 설정
# -------------------------------
st.set_page_config(page_title="서울시 관광지 혼잡도 분석", layout="wide")

# -------------------------------
# 스타일 (눈, 폰트, 배경)
# -------------------------------
st.markdown("""
    <style>
    body {
        background-color: #FFF8DC;
        font-family: 'Noto Sans KR', sans-serif;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Noto Sans KR', sans-serif;
        font-weight: 700;
    }
    p, div, span {
        font-family: 'Noto Sans KR', sans-serif;
    }
    /* 눈 내리는 애니메이션 */
    .snowflake {
        position: fixed;
        top: 0;
        color: #bde0fe;  /* 파스텔 블루 눈 */
        font-size: 25px; /* 눈 크게 */
        animation: fall 8s linear infinite;
        opacity: 0.9;
        pointer-events: none;
        z-index: 9999;
    }
    @keyframes fall {
        0% { transform: translateY(-10px) translateX(0); opacity: 1; }
        100% { transform: translateY(100vh) translateX(20px); opacity: 0; }
    }
    </style>

    <script>
    const snowCount = 30;
    for (let i = 0; i < snowCount; i++) {
        const snow = document.createElement('div');
        snow.className = 'snowflake';
        snow.innerHTML = '❄';
        snow.style.left = Math.random() * 100 + 'vw';
        snow.style.animationDuration = 5 + Math.random() * 5 + 's';
        snow.style.fontSize = 20 + Math.random() * 15 + 'px';
        document.body.appendChild(snow);
    }
    </script>
""", unsafe_allow_html=True)

# -------------------------------
# OpenAI 설정
# -------------------------------
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY"))

# -------------------------------
# 제목
# -------------------------------
st.markdown("<h1 style='text-align:center; color:#222; font-size:55px;'>서울시 실시간 인구데이터 분석</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center; color:#555;'>관광지 혼잡도 실시간 분석 및 AI 인사이트</h3>", unsafe_allow_html=True)
st.markdown("---")

# -------------------------------
# 지역 선택
# -------------------------------
area_name = st.selectbox("📍 분석할 지역을 선택하세요:", ["명동", "홍대", "강남", "여의도", "잠실", "광화문"])

if st.button("데이터 불러오기"):
    with st.spinner("데이터를 불러오는 중입니다..."):
        time.sleep(2)
        st.session_state['congest_lvl'] = "보통"
        st.session_state['congest_msg'] = f"{area_name} 지역은 현재 인구 밀도가 중간 수준입니다."
        st.session_state['df'] = pd.DataFrame({
            "시간대": ["10시", "11시", "12시", "13시", "14시", "15시", "16시"],
            "예상 인구수": [3400, 4100, 5300, 4800, 4500, 3900, 3600]
        })

# -------------------------------
# 데이터 확인 및 표시
# -------------------------------
if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
    congest_lvl = st.session_state['congest_lvl']
    congest_msg = st.session_state['congest_msg']

    # -------------------------------
    # 혼잡도 이미지 카드
    # -------------------------------
    img_map = {
        "여유": "1.png", "보통": "3.png", "혼잡": "5.png", "매우혼잡": "7.png"
    }
    img_file = img_map.get(congest_lvl, "3.png")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(f"images/{img_file}", use_container_width=True)
    with col2:
        st.markdown(f"<h2 style='color:#2b2b2b;'>현재 혼잡도: <b>{congest_lvl}</b></h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:20px;'>{congest_msg}</p>", unsafe_allow_html=True)

    # 🎈 풍선 강도 조정
    if congest_lvl == "여유":
        count = 3
    elif congest_lvl == "보통":
        count = 6
    else:
        count = 10
    for _ in range(count):
        st.balloons()

    st.markdown("---")

    # -------------------------------
    # ChatGPT 분석
    # -------------------------------
    if st.button("💬 ChatGPT 혼잡도 분석 요약 생성"):
        with st.spinner("AI가 데이터를 분석 중입니다..."):
            prompt = f"""
            서울시 관광지 {area_name}의 시간대별 인구 변화 데이터를 분석하여,
            1. 현재 혼잡 원인
            2. 혼잡 완화 방안
            3. 방문하기 좋은 시간대
            4. 관광 팁 (2가지)
            를 간단하게 정리하라.
            데이터:
            {df.to_string(index=False)}
            """
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "도시 데이터 분석가로서 간결하고 명확하게 답변하라."},
                          {"role": "user", "content": prompt}],
                max_tokens=500
            )
            st.session_state['gpt_result'] = response.choices[0].message.content.strip()

    if 'gpt_result' in st.session_state:
        st.markdown(f"""
        <div style='background-color:#fff3cd; padding:25px; border-radius:12px;'>
            <h3>📊 ChatGPT 분석 결과</h3>
            <p style='font-size:18px;'>{st.session_state['gpt_result']}</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

    # -------------------------------
    # 탭 구성
    # -------------------------------
    tab1, tab2, tab3, tab4 = st.tabs(["📈 시간대별 인구", "⚧ 성별 비율", "🎂 연령대 비율", "🗺 위치 지도"])

    with tab1:
        st.subheader("시간대별 예상 인구 변화")
        fig = px.line(df, x="시간대", y="예상 인구수", markers=True,
                      title=f"{area_name} 시간대별 인구 추이",
                      labels={"예상 인구수": "인구수(명)"})
        fig.update_traces(line_color="#0077b6", line_width=4)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        with st.expander("⚧ 성별 비율 보기", expanded=True):
            gender_df = pd.DataFrame({"성별": ["남성", "여성"], "비율": [52, 48]})
            fig2 = px.pie(gender_df, values="비율", names="성별", title=f"{area_name} 성별 비율")
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        with st.expander("🎂 연령대 비율 보기", expanded=True):
            age_df = pd.DataFrame({
                "연령대": ["10대", "20대", "30대", "40대", "50대 이상"],
                "비율": [10, 35, 30, 15, 10]
            })
            fig3 = px.bar(age_df, x="연령대", y="비율", text="비율", title=f"{area_name} 연령대 비율")
            fig3.update_traces(textposition="outside", marker_color="#f4a261")
            st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.subheader("관광지 위치 지도")
        map_df = pd.DataFrame({
            "위도": [37.5665],
            "경도": [126.9780]
        })
        st.map(map_df, zoom=12)

else:
    st.info("분석할 지역을 선택하고 ‘데이터 불러오기’를 눌러주세요.")
