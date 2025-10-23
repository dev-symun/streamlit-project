import streamlit as st
import pandas as pd
import numpy as np
import time
import random
import plotly.graph_objects as go

# ---------------- 기본 설정 ----------------
st.set_page_config(page_title="서울시 실시간 인구데이터 분석", layout="wide")

# 전체 배경 노란색 & 폰트 변경 (Google Fonts)
st.markdown("""
    <style>
    body {
        background-color: #fff9c4;
        font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
    }
    h1, h2, h3, h4, h5 {
        font-family: 'GmarketSansMedium', 'Pretendard', sans-serif;
        color: #333;
    }
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------- 사이드바 ----------------
st.sidebar.header("📍 지역 및 관광지 선택")
region = st.sidebar.selectbox("지역 선택", ["종로구", "중구", "강남구", "마포구", "송파구"])
place = st.sidebar.selectbox(
    "관광지 선택",
    {
        "종로구": ["경복궁", "인사동", "창덕궁"],
        "중구": ["명동", "남산타워", "을지로"],
        "강남구": ["코엑스", "가로수길", "선릉"],
        "마포구": ["홍대거리", "망원한강공원", "상수"],
        "송파구": ["석촌호수", "롯데월드", "올림픽공원"]
    }[region]
)

# ---------------- 눈 내리기 애니메이션 ----------------
def snow_effect():
    st.markdown("""
        <style>
        .snowflake {
            color: #00bcd4;
            font-size: 28px;
            position: fixed;
            top: 0;
            z-index: 9999;
            animation: fall linear infinite;
        }
        @keyframes fall {
            0% { transform: translateY(0px); opacity: 1; }
            100% { transform: translateY(100vh); opacity: 0; }
        }
        </style>
        <script>
        const snowCount = 30;
        for (let i = 0; i < snowCount; i++) {
            const snow = document.createElement('div');
            snow.className = 'snowflake';
            snow.innerHTML = '❄';
            snow.style.left = Math.random() * 100 + 'vw';
            snow.style.animationDuration = (3 + Math.random() * 5) + 's';
            snow.style.fontSize = (16 + Math.random() * 14) + 'px';
            snow.style.opacity = Math.random();
            document.body.appendChild(snow);
        }
        </script>
    """, unsafe_allow_html=True)

snow_effect()

# ---------------- 데이터 로딩 ----------------
with st.spinner(f"{place} 실시간 데이터 불러오는 중..."):
    time.sleep(2)
    hours = list(range(8, 23))
    population = np.random.randint(50, 150, len(hours))
    gender_ratio = {"남성": np.random.randint(45, 55), "여성": np.random.randint(45, 55)}
    age_ratio = {"10대": 10, "20대": 25, "30대": 30, "40대": 20, "50대 이상": 15}

st.success("데이터 로딩 완료!")

# ---------------- 상단 제목 ----------------
st.markdown("<h1 style='text-align:center;'>서울시 실시간 인구데이터 분석</h1>", unsafe_allow_html=True)
st.markdown(f"<h2 style='text-align:center; color:#444;'>📊 {region} {place} 혼잡도 분석 결과</h2>", unsafe_allow_html=True)

# ---------------- 혼잡도 예측 ----------------
crowd_score = np.mean(population)
if crowd_score < 70:
    crowd_level = "여유"
    image_path = "images/1.png"
    intensity = 0.2
elif crowd_score < 100:
    crowd_level = "보통"
    image_path = "images/4.png"
    intensity = 0.5
else:
    crowd_level = "혼잡"
    image_path = "images/7.png"
    intensity = 1.0

# ---------------- 상단 혼잡도 표시 ----------------
col1, col2 = st.columns([1, 3])
with col1:
    st.image(image_path, width=150)
with col2:
    st.markdown(f"<h1 style='font-size:50px; color:#d32f2f;'>{crowd_level}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4>현재 {place}의 예상 혼잡도는 '{crowd_level}' 상태입니다.</h4>", unsafe_allow_html=True)

# 풍선 애니메이션 (혼잡도 강도별)
if intensity >= 0.8:
    st.balloons()
elif intensity >= 0.4:
    for _ in range(2):
        st.balloons()
else:
    pass  # 여유일 때 풍선 없음

# ---------------- 탭 전환 컨테이너 ----------------
tab1, tab2, tab3, tab4 = st.tabs(["⏰ 시간대별 인구", "👥 성별 비율", "🎂 연령대 비율", "🗺 위치 지도"])

with tab1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours, y=population, mode='lines+markers', name='인구 수'))
    fig.update_layout(title=f"{place} 시간대별 예상 인구변화", xaxis_title="시간", yaxis_title="인구(단위: 명)")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    gender_df = pd.DataFrame(list(gender_ratio.items()), columns=['성별', '비율'])
    st.bar_chart(gender_df.set_index('성별'))

with tab3:
    age_df = pd.DataFrame(list(age_ratio.items()), columns=['연령대', '비율'])
    st.bar_chart(age_df.set_index('연령대'))

with tab4:
    st.map(pd.DataFrame({'lat': [37.5665 + random.random()/100], 'lon': [126.9780 + random.random()/100]}))

