import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd

st.title("📊 서울시 실시간 인구 데이터")

# 사용자 입력 (장소명)
area = st.text_input("조회할 지역을 입력하세요", "광화문·덕수궁")

# API KEY 입력
api_key = st.text_input("서울시 OpenAPI 인증키를 입력하세요", type="password")

if st.button("데이터 조회"):
    if not api_key:
        st.warning("API 인증키를 입력하세요.")
    else:
        # API URL 구성
        url = f"http://openapi.seoul.go.kr:8088/{api_key}/xml/citydata_ppltn/1/5/{area}"
        response = requests.get(url)

        if response.status_code == 200:
            root = ET.fromstring(response.content)

            # 현재 인구 정보
            ppltn = root.find(".//SeoulRtd.citydata_ppltn")

            if ppltn is not None:
                area_name = ppltn.findtext("AREA_NM")
                level = ppltn.findtext("AREA_CONGEST_LVL")
                msg = ppltn.findtext("AREA_CONGEST_MSG")
                ppltn_min = ppltn.findtext("AREA_PPLTN_MIN")
                ppltn_max = ppltn.findtext("AREA_PPLTN_MAX")
                male = ppltn.findtext("MALE_PPLTN_RATE")
                female = ppltn.findtext("FEMALE_PPLTN_RATE")
                time = ppltn.findtext("PPLTN_TIME")

                st.subheader(f"📍 {area_name} ({time})")
                st.write(f"혼잡도: {level}")
                st.info(msg)
                st.write(f"현재 인구: {ppltn_min} ~ {ppltn_max} 명")
                st.write(f"남성 비율: {male}%, 여성 비율: {female}%")

                # 예측 인구 데이터 (시간대별)
                fcst_data = []
                for f in ppltn.findall(".//FCST_PPLTN"):
                    fcst_data.append({
                        "시간": f.findtext("FCST_TIME"),
                        "혼잡도": f.findtext("FCST_CONGEST_LVL"),
                        "최소 인구": f.findtext("FCST_PPLTN_MIN"),
                        "최대 인구": f.findtext("FCST_PPLTN_MAX")
                    })

                df = pd.DataFrame(fcst_data)
                st.subheader("⏰ 예측 인구 추이")
                st.dataframe(df)

                # 시각화
                df["최소 인구"] = df["최소 인구"].astype(int)
                df["최대 인구"] = df["최대 인구"].astype(int)
                st.line_chart(df.set_index("시간")[["최소 인구", "최대 인구"]])
            else:
                st.error("데이터를 불러오지 못했습니다. 장소명을 확인하세요.")
        else:
            st.error(f"요청 실패 (HTTP {response.status_code})")
