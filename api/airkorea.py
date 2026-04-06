"""에어코리아 TM 좌표 조회 + 근접 대기측정소 + 실시간 대기오염도 API"""
import requests


TM_COORD_URL = "http://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getTMStdrCrdnt"
NEARBY_STATION_URL = "http://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getNearbyMsrstnList"
AIR_QUALITY_URL = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty"

GRADE_LABEL = {"1": "좋음", "2": "보통", "3": "나쁨", "4": "매우나쁨"}
GRADE_COLOR = {"1": "🟢", "2": "🟡", "3": "🟠", "4": "🔴"}


def get_tm_coordinates(api_key: str, umd_name: str) -> dict:
    """읍면동명으로 TM 기준 좌표 조회."""
    params = {
        "serviceKey": api_key,
        "returnType": "json",
        "numOfRows": 10,
        "pageNo": 1,
        "umdName": umd_name,
    }
    try:
        response = requests.get(TM_COORD_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "total": 0, "locations": [], "error": str(e)}
    except ValueError:
        return {"success": False, "total": 0, "locations": [], "error": "JSON 파싱 오류"}

    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "00":
        return {"success": False, "total": 0, "locations": [], "error": header.get("resultMsg", "API 오류")}

    body = data["response"]["body"]
    total = body.get("totalCount", 0)
    items = body.get("items") or []

    locations = [
        {
            "sidoName": item.get("sidoName", ""),
            "sggName": item.get("sggName", ""),
            "umdName": item.get("umdName", ""),
            "tmX": item.get("tmX", ""),
            "tmY": item.get("tmY", ""),
        }
        for item in items
    ]
    return {"success": True, "total": total, "locations": locations, "error": None}


def get_nearby_stations(api_key: str, tm_x: str, tm_y: str) -> dict:
    """TM 좌표 기준 근접 대기측정소 조회."""
    params = {
        "serviceKey": api_key,
        "tmX": tm_x,
        "tmY": tm_y,
        "ver": 1.1,
        "returnType": "json",
    }
    try:
        response = requests.get(NEARBY_STATION_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "total": 0, "stations": [], "error": str(e)}
    except ValueError:
        return {"success": False, "total": 0, "stations": [], "error": "JSON 파싱 오류"}

    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "00":
        return {"success": False, "total": 0, "stations": [], "error": header.get("resultMsg", "API 오류")}

    body = data["response"]["body"]
    total = body.get("totalCount", 0)
    items = body.get("items") or []

    stations = [
        {
            "stationName": item.get("stationName", ""),
            "addr": item.get("addr", ""),
            "tm": item.get("tm", ""),
        }
        for item in items
    ]
    return {"success": True, "total": total, "stations": stations, "error": None}


def get_air_quality(api_key: str, station_name: str) -> dict:
    """
    측정소명으로 실시간 대기오염도 조회.

    Returns:
        {
            "success": bool,
            "station": str,
            "dataTime": str,
            "items": [{"name": ..., "value": ..., "grade": ..., "grade_label": ..., "grade_color": ...}],
            "error": str | None
        }
    """
    params = {
        "serviceKey": api_key,
        "returnType": "json",
        "numOfRows": 1,
        "pageNo": 1,
        "stationName": station_name,
        "dataTerm": "DAILY",
        "ver": "1.3",
    }
    try:
        response = requests.get(AIR_QUALITY_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "station": station_name, "dataTime": "", "items": [], "error": str(e)}
    except ValueError:
        return {"success": False, "station": station_name, "dataTime": "", "items": [], "error": "JSON 파싱 오류"}

    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "00":
        return {"success": False, "station": station_name, "dataTime": "", "items": [], "error": header.get("resultMsg", "API 오류")}

    raw_items = (data.get("response", {}).get("body", {}).get("items") or [])
    if not raw_items:
        return {"success": False, "station": station_name, "dataTime": "", "items": [], "error": "측정 데이터 없음"}

    row = raw_items[0]
    data_time = row.get("dataTime", "")

    pollutants = [
        ("pm10Value",  "PM10 미세먼지",    "㎍/㎥", "pm10Grade"),
        ("pm25Value",  "PM2.5 초미세먼지", "㎍/㎥", "pm25Grade"),
        ("o3Value",    "오존(O₃)",         "ppm",   "o3Grade"),
        ("no2Value",   "이산화질소(NO₂)",  "ppm",   "no2Grade"),
        ("coValue",    "일산화탄소(CO)",   "ppm",   "coGrade"),
        ("so2Value",   "아황산가스(SO₂)", "ppm",   "so2Grade"),
    ]

    items = []
    for val_key, name, unit, grade_key in pollutants:
        value = row.get(val_key, "-")
        grade = row.get(grade_key, "")
        items.append({
            "name": name,
            "value": value,
            "unit": unit,
            "grade": grade,
            "grade_label": GRADE_LABEL.get(grade, "-"),
            "grade_color": GRADE_COLOR.get(grade, "⚪"),
        })

    return {"success": True, "station": station_name, "dataTime": data_time, "items": items, "error": None}
