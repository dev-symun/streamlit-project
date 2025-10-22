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
# API 기본값
# -------------------------------
API_KEY = st.secrets["API_KEY"]
BASE_URL = "http://openapi.seoul.go.kr:8088"
TYPE = "xml"
SERVICE = "citydata_ppltn"
START_INDEX = 1
END_INDEX = 116  # 서울시 주요 장소 전체 범위

# -------------------------------
# API로 모든 장소 불러오기
# -------------------------------
@st.cache_data
def get_all_places():
    url = f"{BASE_URL}/{API_KEY}/{TYPE}/{SERVICE}/{START_INDEX}/{END_INDEX}"
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        st.error(f"API 요청 실패: {response.status_code}")
        return pd.DataFrame()
    
    root = ET.fromstring(response.content)
    items = root.findall(".//SeoulRtd.citydata_ppltn")
    data = []
    for item in items:
        # 기본 데이터 추출
        record = {
            "AREA_NM": item.findtext("AREA_NM"),
            "AREA_CD": item.findtext("AREA_CD"),
            "AREA_CONGEST_LVL": item.findtext("AREA_CONGEST_LVL"),
            "AREA_CONGEST_MSG": item.findtext("AREA_CONGEST_MSG"),
            "AREA_PPLTN_MIN": item.findtext("AREA_PPLTN_MIN"),
            "AREA_PPLTN_MAX": item.findtext("AREA_PPLTN_MAX"),
            "MALE_PPLTN_RATE": item.findtext("MALE_PPLTN_RATE"),
            "FEMALE_PPLTN_RATE": item.findtext("FEMALE_PPLTN_RATE"),
            "PPLTN_RATE_0": item.findtext("PPLTN_RATE_0"),
            "PPLTN_RATE_10": item.findtext("PPLTN_RATE_10"),
            "PPLTN_RATE_20": item.findtext("PPLTN_RATE_20"),
            "PPLTN_RATE_30": item.findtext("PPLTN_RATE_30"),
            "PPLTN_RATE_40": item.findtext("PPLTN_RATE_40"),
            "PPLTN_RATE_50": item.findtext("PPLTN_RATE_50"),
            "PPLTN_RATE_60": item.findtext("PPLTN_RATE_60"),
            "PPLTN_RATE_70": item.findtext("PPLTN_RATE_70"),
            "RESNT_PPLTN_RATE": item.findtext("RESNT_PPLTN_RATE"),
            "NON_RESNT_PPLTN_RATE": item.findtext("NON_RESNT_PPLTN_RATE"),
            "REPLACE_YN": item.findtext("REPLACE_YN"),
            "PPLTN_TIME": item.findtext("PPLTN_TIME"),
            "FCST_YN": item.findtext("FCST_YN"),
        }

        # 예측 인구 데이터 추출
        fcst_list = []
        for fcst in item.findall(".//FCST_PPLTN"):
            fcst_list.append({
                "FCST_TIME": fcst.findtext("FCST_TIME"),
                "FCST_CONGEST_LVL": fcst.findtext("FCST_CONGEST_LVL"),
                "FCST_PPLTN_MIN": fcst.findtext("FCST_PPLTN_MIN"),
                "FCST_PPLTN_MAX": fcst.findtext("FCST_PPLTN_MAX"),
            })
        record["FCST_PPLTN"] = fcst_list
        data.append(record)
    
    return pd.DataFrame(data)

places_df = get_all_places()

if places_df.empty:
    st.warning("장소 데이터가 없습니다. API 키와 범위를 확인하세요.")
else:
    # -------------------------------
    # 사용자 선택
    # -------------------------------
    area = st.selectbox("장소 선택", sorted(places_df["AREA_NM"].dropna().unique()))
    
    selected_data = places_df.loc[places_df["AREA_NM"] == area].iloc[0]

    st.subheader(f"📍 {selected_data['AREA_NM']} (업데이트: {selected_data['PPLTN_TIME']})")

    # -------------------------------
    # 기본 지표
    # -------------------------------
    col1, col2 = st.columns(2)
    col1.metric("혼잡도", selected_data["AREA_CONGEST_LVL"])
    col2.metric("현재 인구 (명)", f"{int(selected_data['AREA_PPLTN_MIN']):,} ~ {int(selected_data['AREA_PPLTN_MAX']):,}")
    st.info(selected_data["AREA_CONGEST_MSG"])

    # -------------------------------
    # 성별
    # -------------------------------
    st.write("### 👥 성별 비율")
    import plotly.express as px
    sex_df = pd.DataFrame({
        "성별": ["남성", "여성"],
        "비율": [float(selected_data["MALE_PPLTN_RATE"]), float(selected_data["FEMALE_PPLTN_RATE"])]
    })
    fig = px.pie(sex_df, names="성별", values="비율", title="성별 비율", hole=0.3)
    st.plotly_chart(fig, use_container_width=True)
    major_sex = sex_df.loc[sex_df["비율"].idxmax(), "성별"]
    st.write(f"가장 많은 성별: **{major_sex}**")

    # -------------------------------
    # 연령별 비율
    # -------------------------------
    age_cols = ["PPLTN_RATE_0","PPLTN_RATE_10","PPLTN_RATE_20","PPLTN_RATE_30",
                "PPLTN_RATE_40","PPLTN_RATE_50","PPLTN_RATE_60","PPLLN_RATE_70"]
    st.write("### 👶👵 연령대 비율")
    age_df = pd.DataFrame({
        "연령대": ["0~10","10대","20대","30대","40대","50대","60대","70대 이상"],
        "비율": [float(selected_data[c]) for c in ["PPLTN_RATE_0","PPLTN_RATE_10","PPLTN_RATE_20","PPLTN_RATE_30",
                                                    "PPLTN_RATE_40","PPLTN_RATE_50","PPLTN_RATE_60","PPLTN_RATE_70"]]
    })
    st.bar_chart(age_df.set_index("연령대"))

    # -------------------------------
    # 예측 데이터
    # -------------------------------
    if selected_data["FCST_YN"] == "Y":
        fcst_df = pd.DataFrame(selected_data["FCST_PPLTN"])
        st.write("### ⏰ 시간대별 인구 예측")
        st.dataframe(fcst_df)
        st.line_chart(fcst_df.set_index("FCST_TIME")[["FCST_PPLTN_MIN","FCST_PPLTN_MAX"]])

    # -------------------------------
    # 전체 데이터 출력
    # -------------------------------
    st.write("### 🔍 API 원본 데이터")
    st.json(selected_data.to_dict())
