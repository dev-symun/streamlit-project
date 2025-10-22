import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from urllib.parse import quote

# -------------------------------
# 기본 설정
# -------------------------------
st.set_page_config(page_title="서울시 실시간 인구 데이터", page_icon="📊", layout="wide")
st.title("📊 서울시 실시간 인구 데이터 (citydata_ppltn)")

# -------------------------------
# 사용자 입력
# -------------------------------
st.markdown("서울의 주요 지역 중 하나를 입력하세요 (예: 광화문·덕수궁, 명동, 강남 MICE 관광특구 등)")
area = st.text_input("조회할 지역명 입력", "광화문·덕수궁")

# -------------------------------
# API 요청 URL 구성
# -------------------------------
API_KEY = "78665a616473796d3339716b4d446c"
BASE_URL = "http://openapi.seoul.go.kr:8088"
TYPE = "xml"
SERVICE = "citydata_ppltn"
START_INDEX = 1
END_INDEX = 5

# -------------------------------
# API 요청
# -------------------------------
if st.button("📡 데이터 불러오기"):
    try:
        encoded_area = quote(area)
        url = f"{BASE_URL}/{API_KEY}/{TYPE}/{SERVICE}/{START_INDEX}/{END_INDEX}/{encoded_area}"

        response = requests.get(url)
        if response.status_code != 200:
            st.error(f"요청 실패 (HTTP {response.status_code})")
        else:
            root = ET.fromstring(response.content)
            ppltn = root.find(".//SeoulRtd.citydata_ppltn")

            if ppltn is None:
                st.error("⚠️ 해당 지역의 데이터를 찾을 수 없습니다. (지역명을 정확히 입력하세요)")
            else:
                # -------------------------------
                # 기본 인구 데이터 추출
                # -------------------------------
                area_name = ppltn.findtext("AREA_NM")
                congest_lvl = ppltn.findtext("AREA_CONGEST_LVL")
                congest_msg = ppltn.findtext("AREA_CONGEST_MSG")
                ppltn_min = int(ppltn.findtext("AREA_PPLTN_MIN"))
                ppltn_max = int(ppltn.findtext("AREA_PPLTN_MAX"))
                male = float(ppltn.findtext("MALE_PPLTN_RATE"))
                female = float(ppltn.findtext("FEMALE_PPLTN_RATE"))
                ppltn_time = ppltn.findtext("PPLTN_TIME")

                # -------------------------------
                # 시각적 요약
                # -------------------------------
                st.subheader(f"📍 {area_name} (업데이트: {ppltn_time})")
                col1, col2 = st.columns(2)
                col1.metric("혼잡도", congest_lvl)
                col2.metric("현재 인구 (명)", f"{ppltn_min:,} ~ {ppltn_max:,}")

                st.info(congest_msg)

                # -------------------------------
                # 성별 비율
                # -------------------------------
                st.write("### 👥 성별 비율")
                st.progress(int(male))
                st.write(f"남성 {male}% / 여성 {female}%")

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
                    df = pd.DataFrame(fcst_data)
                    st.write("### ⏰ 시간대별 인구 예측")
                    st.dataframe(df)

                    # -------------------------------
                    # 시각화
                    # -------------------------------
                    st.line_chart(df.set_index("시간")[["예상 최소 인구", "예상 최대 인구"]])
                else:
                    st.warning("예측 데이터가 없습니다.")

    except Exception as e:
        st.error(f"오류 발생: {e}")
