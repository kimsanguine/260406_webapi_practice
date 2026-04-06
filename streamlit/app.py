"""공공 Web API 실습 — Streamlit 인터랙티브 데모"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.address import search_address
from api.weather import get_weather
from api.airkorea import get_tm_coordinates, get_nearby_stations, get_air_quality

load_dotenv()


def _get_env_key() -> str:
    """Streamlit Cloud st.secrets → .env → 빈 문자열 순으로 API Key 로드."""
    try:
        return st.secrets.get("SERVICE_KEY", "")
    except Exception:
        return os.getenv("SERVICE_KEY", "")


# ── 도시 정보 (격자 좌표 + 대표 측정소) ──────────────────────
CITY_INFO = {
    "서울":  {"nx": 60,  "ny": 127, "station": "중구"},
    "인천":  {"nx": 55,  "ny": 124, "station": "석바위"},
    "수원":  {"nx": 60,  "ny": 121, "station": "경수대로(동수원)"},
    "대전":  {"nx": 67,  "ny": 100, "station": "월평동"},
    "청주":  {"nx": 69,  "ny": 107, "station": "복대동"},
    "대구":  {"nx": 89,  "ny": 90,  "station": "만촌동"},
    "전주":  {"nx": 63,  "ny": 89,  "station": "서신동"},
    "광주":  {"nx": 58,  "ny": 74,  "station": "운암동"},
    "울산":  {"nx": 102, "ny": 84,  "station": "명륜동"},
    "부산":  {"nx": 98,  "ny": 76,  "station": "재송동"},
    "제주":  {"nx": 52,  "ny": 38,  "station": "노형로"},
}

GRADE_COLOR = {"1": "🟢", "2": "🟡", "3": "🟠", "4": "🔴"}
GRADE_LABEL = {"1": "좋음", "2": "보통", "3": "나쁨", "4": "매우나쁨"}
RAIN_EMOJI  = {"없음": "☀️", "비": "🌧️", "비/눈": "🌨️", "눈": "❄️", "빗방울": "🌦️"}


def fetch_city_summary(api_key: str, city: str) -> dict:
    """날씨 + 대기오염도를 병렬 호출해 도시 요약 반환."""
    info = CITY_INFO[city]
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_weather = ex.submit(get_weather, api_key, info["nx"], info["ny"])
        f_air     = ex.submit(get_air_quality, api_key, info["station"])
        weather   = f_weather.result()
        air       = f_air.result()
    return {"city": city, "weather": weather, "air": air}


# ── 페이지 설정 ───────────────────────────────────────────────
st.set_page_config(page_title="공공 Web API 실습", page_icon="🌐", layout="wide")
st.title("🌐 공공 Web API 실습 데모")
st.caption("우체국 · 기상청 · 에어코리아 공공 API를 직접 호출해보세요.")

# ── 사이드바 ─────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")
    env_key = _get_env_key()
    api_key_input = st.text_input("공공데이터포털 API Key", value=env_key, type="password")
    api_key = requests.utils.unquote(api_key_input) if api_key_input else ""

    if api_key:
        st.success("API Key 로드됨")
    else:
        st.warning(".env 파일에 SERVICE_KEY를 설정하거나 직접 입력하세요.")
    st.divider()
    st.markdown("**사용 API**\n- 🏣 우체국 주소 검색\n- ⛅ 기상청 초단기실황\n- 🌫️ 에어코리아 대기오염도")

tab0, tab1, tab2, tab3 = st.tabs(["📊 지역별 요약", "🏣 주소 검색", "⛅ 날씨 조회", "🌫️ 대기오염도"])

# ════════════════════════════════════════════════════════════
# TAB 0: 지역별 요약 대시보드
# ════════════════════════════════════════════════════════════
with tab0:
    st.subheader("지역별 날씨 + 대기오염도 요약")

    selected_cities = st.multiselect(
        "조회할 도시 선택",
        list(CITY_INFO.keys()),
        default=["서울", "대전", "부산", "대구", "광주"],
    )

    run_btn = st.button("한번에 조회", type="primary", disabled=not api_key or not selected_cities)

    if run_btn:
        with st.spinner(f"{len(selected_cities)}개 도시 동시 조회 중..."):
            results = {}
            with ThreadPoolExecutor(max_workers=len(selected_cities)) as ex:
                futures = {ex.submit(fetch_city_summary, api_key, c): c for c in selected_cities}
                for future in as_completed(futures):
                    city = futures[future]
                    results[city] = future.result()
        st.session_state["summary_results"] = results
        st.session_state["summary_cities"]  = selected_cities

    if "summary_results" in st.session_state:
        results = st.session_state["summary_results"]
        cities  = st.session_state["summary_cities"]

        # 3열 그리드
        COLS = 3
        rows = [cities[i:i+COLS] for i in range(0, len(cities), COLS)]

        for row in rows:
            cols = st.columns(COLS)
            for col, city in zip(cols, row):
                data = results.get(city)
                if not data:
                    continue
                w = data["weather"]
                a = data["air"]

                with col:
                    # 날씨 값 추출
                    w_map = {i["category"]: i for i in w.get("items", [])} if w["success"] else {}
                    temp  = w_map.get("T1H", {}).get("value", "-")
                    hum   = w_map.get("REH", {}).get("value", "-")
                    pty   = w_map.get("PTY", {}).get("value", "없음")
                    rain_icon = RAIN_EMOJI.get(pty, "🌤️")

                    # 대기오염도 값 추출
                    pm10_item  = next((i for i in a.get("items", []) if "PM10" in i["name"]), None) if a["success"] else None
                    pm25_item  = next((i for i in a.get("items", []) if "PM2.5" in i["name"]), None) if a["success"] else None
                    pm10_val   = f"{pm10_item['value']} ㎍/㎥" if pm10_item else "-"
                    pm25_val   = f"{pm25_item['value']} ㎍/㎥" if pm25_item else "-"
                    pm10_grade = GRADE_COLOR.get(pm10_item["grade"], "⚪") if pm10_item else "⚪"
                    pm25_grade = GRADE_COLOR.get(pm25_item["grade"], "⚪") if pm25_item else "⚪"

                    with st.container(border=True):
                        st.markdown(f"### {rain_icon} {city}")
                        if w["success"]:
                            st.metric("기온", f"{temp} °C")
                            c1, c2 = st.columns(2)
                            c1.metric("습도", f"{hum} %")
                            c2.metric("강수", pty)
                        else:
                            st.caption("날씨 조회 실패")

                        st.divider()
                        st.caption("대기오염도")
                        if a["success"]:
                            c1, c2 = st.columns(2)
                            c1.metric(f"{pm10_grade} PM10",  pm10_val)
                            c2.metric(f"{pm25_grade} PM2.5", pm25_val)
                            if pm10_item:
                                grade_label = GRADE_LABEL.get(pm10_item["grade"], "-")
                                st.caption(f"측정소: {CITY_INFO[city]['station']} | 종합 {grade_label}")
                        else:
                            st.caption("대기오염도 조회 실패")

        # 비교 테이블
        if results:
            st.divider()
            st.write("**전체 비교 테이블**")
            table = []
            for city in cities:
                data = results.get(city)
                if not data:
                    continue
                w = data["weather"]
                a = data["air"]
                w_map = {i["category"]: i for i in w.get("items", [])} if w["success"] else {}
                pm10_item = next((i for i in a.get("items", []) if "PM10"  in i["name"]), None) if a["success"] else None
                pm25_item = next((i for i in a.get("items", []) if "PM2.5" in i["name"]), None) if a["success"] else None

                pty_val = w_map.get("PTY", {}).get("value", "-")
                table.append({
                    "도시":       city,
                    "기온(°C)":   w_map.get("T1H", {}).get("value", "-"),
                    "습도(%)":    w_map.get("REH", {}).get("value", "-"),
                    "강수":       f"{RAIN_EMOJI.get(pty_val, '')} {pty_val}",
                    "PM10":       f"{pm10_item['grade_color']} {pm10_item['value']} ({pm10_item['grade_label']})" if pm10_item else "-",
                    "PM2.5":      f"{pm25_item['grade_color']} {pm25_item['value']} ({pm25_item['grade_label']})" if pm25_item else "-",
                })
            st.dataframe(table, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════
# TAB 1: 주소 검색
# ════════════════════════════════════════════════════════════
with tab1:
    st.subheader("우체국 주소 검색 API")
    st.markdown("`XML` 응답 → `xmltodict`로 딕셔너리 변환")

    col1, col2 = st.columns([3, 1])
    with col1:
        keyword = st.text_input("주소 입력", placeholder="예: 둔산대로 135, 세종대로 110")
    with col2:
        search_type = st.selectbox("검색 방식", ["도로명 (road)", "지번 (jibun)"])
        search_type_val = "road" if "road" in search_type else "jibun"

    if st.button("검색", type="primary", key="addr_btn", disabled=not api_key or not keyword):
        with st.spinner("API 호출 중..."):
            result = search_address(api_key, keyword, search_type_val)
        st.session_state["addr_result"]  = result
        st.session_state["addr_keyword"] = keyword

    if "addr_result" in st.session_state:
        result = st.session_state["addr_result"]
        st.caption(f"검색어: **{st.session_state.get('addr_keyword', '')}**")
        if result["success"] and result["total"] > 0:
            st.success(f"총 {result['total']}건")
            for item in result["results"]:
                with st.container(border=True):
                    col_a, col_b = st.columns([1, 4])
                    col_a.metric("우편번호", item["zipNo"])
                    with col_b:
                        st.write(f"**도로명** {item['lnmAdres']}")
                        st.write(f"**지번** {item['rnAdres']}")
        elif result["success"]:
            st.warning("검색 결과가 없습니다.")
        else:
            st.error(f"오류: {result['error']}")

    with st.expander("📖 핵심 코드"):
        st.code("""
import requests, xmltodict

url    = 'http://openapi.epost.go.kr/.../getNewAddressListAreaCd'
params = {"ServiceKey": API_KEY, "searchSe": "road", "srchwrd": "둔산대로 135"}

xml_data = requests.get(url, params=params).text
data     = xmltodict.parse(xml_data)
result   = data['NewAddressListResponse']['newAddressListAreaCd']
print(result['zipNo'], result['lnmAdres'])
        """, language="python")

# ════════════════════════════════════════════════════════════
# TAB 2: 날씨 조회
# ════════════════════════════════════════════════════════════
with tab2:
    st.subheader("기상청 초단기실황 API")
    st.markdown("`JSON` 응답 | 매 정시 발표, 현재 기상 실황값")

    col1, col2 = st.columns([2, 1])
    with col1:
        city_w = st.selectbox("도시 선택", list(CITY_INFO.keys()), key="weather_city_sel")
    nx_w, ny_w = CITY_INFO[city_w]["nx"], CITY_INFO[city_w]["ny"]
    col2.info(f"격자 좌표: nx={nx_w}, ny={ny_w}")

    if st.button("날씨 조회", type="primary", key="weather_btn", disabled=not api_key):
        with st.spinner("API 호출 중..."):
            result = get_weather(api_key, nx_w, ny_w)
        st.session_state["weather_result"] = result
        st.session_state["weather_city"]   = city_w

    if "weather_result" in st.session_state:
        result = st.session_state["weather_result"]
        queried = st.session_state.get("weather_city", "")
        st.caption(f"도시: **{queried}** | 발표: {result.get('base_date','')} {result.get('base_time','')}")
        if result["success"]:
            priority = ["T1H", "REH", "PTY", "RN1", "WSD", "VEC"]
            p_map = {i["category"]: i for i in result["items"]}
            show  = [p_map[c] for c in priority if c in p_map]
            cols  = st.columns(len(show))
            for col, item in zip(cols, show):
                col.metric(item["name"], f"{item['value']}{item['unit']}")
            st.divider()
            st.dataframe(
                [{"항목": i["name"], "값": f"{i['value']}{i['unit']}"} for i in result["items"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.error(f"오류: {result['error']}")

    with st.expander("💡 격자 좌표란?"):
        st.markdown("""
기상청은 전국을 **5km × 5km 격자**로 나눠 예보합니다.
WGS84 경위도가 아닌 **기상청 전용 격자 좌표계**를 사용합니다.

| 도시 | nx | ny | | 도시 | nx | ny |
|------|----|----|---|------|----|----|
| 서울 | 60 | 127 | | 대구 | 89 | 90 |
| 대전 | 67 | 100 | | 부산 | 98 | 76 |
| 광주 | 58 | 74  | | 제주 | 52 | 38 |
        """)

    with st.expander("📖 핵심 코드"):
        st.code("""
import requests, datetime
from pytz import timezone

local_time = datetime.datetime.now(timezone('Asia/Seoul'))
base_hour  = local_time.hour if local_time.minute >= 30 else local_time.hour - 1
base_time  = f"{base_hour:02d}00"

params = {"ServiceKey": API_KEY, "dataType": "JSON",
          "base_date": local_time.strftime('%Y%m%d'),
          "base_time": base_time, "nx": 67, "ny": 100}
items = requests.get(url, params=params).json()['response']['body']['items']['item']
        """, language="python")

# ════════════════════════════════════════════════════════════
# TAB 3: 대기오염도
# ════════════════════════════════════════════════════════════
with tab3:
    st.subheader("에어코리아 실시간 대기오염도 API")
    st.markdown("**흐름**: 읍면동명 → TM 좌표 → 근접 측정소 → **실시간 대기오염도**")

    umd_name = st.text_input("읍/면/동명 입력", placeholder="예: 봉명동, 여의도동, 해운대동")

    if st.button("조회", type="primary", key="air_btn", disabled=not api_key or not umd_name):
        with st.spinner("TM 좌표 조회 중..."):
            coord_result = get_tm_coordinates(api_key, umd_name)
        st.session_state["air_coord"] = coord_result
        st.session_state["air_umd"]   = umd_name
        st.session_state.pop("air_station_result", None)
        st.session_state.pop("air_quality_result", None)

    if "air_coord" in st.session_state:
        coord_result = st.session_state["air_coord"]
        if not coord_result["success"]:
            st.error(f"오류: {coord_result['error']}")
        elif coord_result["total"] == 0:
            st.warning("검색 결과가 없습니다.")
        else:
            locations = coord_result["locations"]
            selected_idx = st.selectbox(
                f"'{st.session_state['air_umd']}' 지역 선택",
                range(len(locations)),
                format_func=lambda i: f"{locations[i]['sidoName']} {locations[i]['sggName']} {locations[i]['umdName']}",
                key="air_loc_select",
            )
            selected_loc = locations[selected_idx]

            if st.button("이 지역 측정소 조회", key="station_btn"):
                with st.spinner("근접 측정소 조회 중..."):
                    station_result = get_nearby_stations(api_key, selected_loc["tmX"], selected_loc["tmY"])
                st.session_state["air_station_result"] = station_result
                st.session_state.pop("air_quality_result", None)

    if "air_station_result" in st.session_state:
        station_result = st.session_state["air_station_result"]
        if not station_result["success"]:
            st.error(f"오류: {station_result['error']}")
        else:
            stations = station_result["stations"]
            selected_station_idx = st.selectbox(
                f"근접 측정소 {station_result['total']}개",
                range(len(stations)),
                format_func=lambda i: f"{stations[i]['stationName']} ({stations[i]['tm']}km) — {stations[i]['addr']}",
                key="station_select",
            )
            selected_station = stations[selected_station_idx]["stationName"]

            if st.button(f"**{selected_station}** 대기오염도 조회", type="primary", key="quality_btn"):
                with st.spinner("대기오염도 조회 중..."):
                    quality_result = get_air_quality(api_key, selected_station)
                st.session_state["air_quality_result"] = quality_result

    if "air_quality_result" in st.session_state:
        quality_result = st.session_state["air_quality_result"]
        if not quality_result["success"]:
            st.error(f"오류: {quality_result['error']}")
        else:
            st.divider()
            st.write(f"**{quality_result['station']}** 실시간 대기오염도")
            st.caption(f"측정 시각: {quality_result['dataTime']}")
            items = quality_result["items"]
            main  = [i for i in items if "PM" in i["name"]]
            other = [i for i in items if "PM" not in i["name"]]

            cols = st.columns(len(main))
            for col, item in zip(cols, main):
                col.metric(f"{item['grade_color']} {item['name']}",
                           f"{item['value']} {item['unit']}", item["grade_label"], delta_color="off")
            cols2 = st.columns(len(other))
            for col, item in zip(cols2, other):
                col.metric(f"{item['grade_color']} {item['name']}",
                           f"{item['value']} {item['unit']}", item["grade_label"], delta_color="off")

    with st.expander("📖 핵심 코드"):
        st.code("""
# 3단계 흐름
# 1) TM 좌표: umdName → tmX, tmY
# 2) 근접 측정소: tmX, tmY → stationName
# 3) 대기오염도: stationName → pm10, pm25, o3, no2, co, so2

data3 = requests.get('...getMsrstnAcctoRltmMesureDnsty',
    params={..., 'stationName': '월평동', 'dataTerm': 'DAILY'}).json()
row = data3['response']['body']['items'][0]
print(row['pm10Value'], row['pm25Value'])
        """, language="python")
