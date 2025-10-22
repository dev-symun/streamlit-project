import streamlit as st
import requests
import pandas as pd

# 1️⃣ API 키 불러오기
API_KEY = st.secrets["API_KEY"]

# 2️⃣ 서울시 25개 구 리스트
SEOUL_DISTRICTS = [
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구",
    "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구",
    "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구",
    "종로구", "중구", "중랑구"
]

# 3️⃣ 예시용 API URL (실제 사용 시 수정)
API_URL = "https://api.example.com/places"  # 실제 API URL로 변경 필요

@st.cache_data
def get_places():
    """API 호출해서 장소 데이터 가져오기"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    res = requests.get(API_URL, headers=headers)
    data = res.json()

    # API 응답 예시: [{"name": "롯데월드", "address": "서울특별시 송파구 잠실동 240"}, ...]
    df = pd.DataFrame(data)

    # 구 이름 추출
    def extract_district(address):
        for gu in SEOUL_DISTRICTS:
            if gu in address:
                return gu
        return None

    df["구"] = df["address"].apply(extract_district)
    return df.dropna(subset=["구"])

# 4️⃣ 메인 앱
st.title("서울시 지역별 장소 탐색 🗺️")

with st.spinner("데이터 불러오는 중..."):
    places_df = get_places()

# 5️⃣ 구 선택 콤보박스
selected_gu = st.selectbox("📍 먼저 구를 선택하세요", sorted(places_df["구"].unique()))

# 6️⃣ 선택한 구에 속한 장소 필터링
filtered_places = places_df[places_df["구"] == selected_gu]

# 7️⃣ 장소 선택 콤보박스
selected_place = st.selectbox("🏠 장소를 선택하세요", filtered_places["name"].tolist())

# 8️⃣ 선택한 장소의 정보 표시
place_info = filtered_places[filtered_places["name"] == selected_place].iloc[0]
st.markdown(f"### 📖 {selected_place}")
st.write(f"**주소:** {place_info['address']}")

# 추가 정보가 있다면 여기에 표시
if "description" in place_info:
    st.write(f"**설명:** {place_info['description']}")
